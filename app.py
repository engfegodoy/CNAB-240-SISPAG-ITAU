import streamlit as st
from pathlib import Path
import tempfile

from pdf_extract import extrair_gnres_do_pdf_com_debug
from cnab import gerar_cnab_itau_gnre_segmento_o, proximo_nome_cnab

st.set_page_config(page_title="Gerador CNAB GNRE (Itaú)", layout="centered")

st.title("Gerador CNAB240 Itaú – GNRE (Segmento O)")
st.write("Envie o PDF com as guias GNRE e baixe o arquivo CNAB pronto.")

uploaded = st.file_uploader("PDF das GNREs", type=["pdf"])

STATE_DIR = Path(".cnab_state")
STATE_DIR.mkdir(exist_ok=True)

if uploaded:
    # salva o PDF em um arquivo temporário
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
            st.dataframe(ok)

        if falhas:
            st.subheader("⚠️ Páginas que falharam (e por quê)")
            st.dataframe(falhas)

        if len(ok) == 0:
            st.error("Não encontrei guias válidas no PDF (faltou UF/vencimento/valor/linha digitável).")
        else:
            # Nome exigido: 8 caracteres, ex CNAB0001
            nome_base = proximo_nome_cnab(STATE_DIR / "seq.txt")  # "CNAB0001"
            nome_arquivo = f"{nome_base}.txt"

            if st.button("Gerar CNAB"):
                out_bytes = gerar_cnab_itau_gnre_segmento_o(ok, nome_base)

                st.download_button(
                    label=f"Baixar {nome_arquivo}",
                    data=out_bytes,
                    file_name=nome_arquivo,
                    mime="text/plain"
                )
                st.success("CNAB gerado com sucesso!")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
