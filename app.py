import streamlit as st
from pathlib import Path
import tempfile
import hmac

from pdf_extract import extrair_gnres_do_pdf_com_debug
from cnab import gerar_cnab_itau_gnre_segmento_o, proximo_nome_cnab


# =============================
# CONFIG STREAMLIT
# =============================
st.set_page_config(
    page_title="GNRE Reader Pro",
    layout="centered"
)


# =============================
# LOGIN
# =============================
def check_login() -> bool:
    if st.session_state.get("auth_ok"):
        return True

    st.markdown("## 🔐 Acesso restrito")

    user = st.text_input("Usuário")
    token = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        expected_user = st.secrets.get("USERNAME", "")
        expected_token = st.secrets.get("TOKEN", "")

        ok = (
            hmac.compare_digest(user, expected_user)
            and hmac.compare_digest(token, expected_token)
        )

        if ok:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")
            st.session_state["auth_ok"] = False

    return False


# 🔒 trava o app
if not check_login():
    st.stop()


# =============================
# BOTÃO SAIR (TOPO)
# =============================
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🚪 Sair"):
        st.session_state["auth_ok"] = False
        st.rerun()


# =============================
# HEADER DO APP
# =============================
st.title("GNRE Reader Pro")
st.caption("Extração por página e geração de CNAB 240 Itaú (SISPAG – Segmento O)")


# =============================
# UPLOAD PDF
# =============================
uploaded = st.file_uploader(
    "📄 Clique para enviar ou arraste o PDF das GNREs",
    type=["pdf"]
)

STATE_DIR = Path(".cnab_state")
STATE_DIR.mkdir(exist_ok=True)


# =============================
# PROCESSAMENTO
# =============================
if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded.read())
        pdf_path = tmp.name

    st.success("PDF carregado. Extraindo guias...")

    try:
        ok, falhas = extrair_gnres_do_pdf_com_debug(pdf_path)

        st.write(f"Guias completas: **{len(ok)}**")
        st.write(f"Páginas com falha: **{len(falhas)}**")

        if ok:
            st.subheader("✅ Guias prontas para CNAB")
            st.dataframe(ok, use_container_width=True)

        if falhas:
            st.subheader("⚠️ Páginas que falharam (e por quê)")
            st.dataframe(falhas, use_container_width=True)

        if len(ok) == 0:
            st.error(
                "Não encontrei guias válidas no PDF "
                "(faltou UF, vencimento, valor ou linha digitável)."
            )
        else:
            nome_base = proximo_nome_cnab(STATE_DIR / "seq.txt")  # CNAB0001
            nome_arquivo = f"{nome_base}.txt"

            if st.button("📥 Gerar CNAB"):
                out_bytes = gerar_cnab_itau_gnre_segmento_o(ok, nome_base)

                st.download_button(
                    label=f"Baixar {nome_arquivo}",
                    data=out_bytes,
                    file_name=nome_arquivo,
                    mime="text/plain"
                )

                st.success("CNAB gerado com sucesso!")

    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
