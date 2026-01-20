import re
import pdfplumber
from collections import Counter

UFS = {
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
    "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
}

def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")

def _extrair_linha_digitavel_unica(texto: str) -> str | None:
    candidatos = re.findall(r"8(?:\s*\d){43,59}", texto, flags=re.S)
    normalizados = []

    for c in candidatos:
        dig = _only_digits(c)
        if dig.startswith("8") and 44 <= len(dig) <= 60:
            normalizados.append(dig)

    blocos = re.findall(r"(?:\d{1,12}\s+){4,}\d{1,12}", texto, flags=re.S)
    for b in blocos:
        dig = _only_digits(b)
        if dig.startswith("8") and 44 <= len(dig) <= 60:
            normalizados.append(dig)

    if not normalizados:
        return None

    linha = Counter(normalizados).most_common(1)[0][0]

    # Normaliza para 48
    if len(linha) == 49:
        linha = linha[:48]
    return linha

def _extrair_uf_favorecida(texto: str) -> str | None:
    m = re.search(r"UF\s*Favorecida\s*:?\s*([A-Z]{2})\b", texto, flags=re.I | re.S)
    if m:
        uf = m.group(1).upper()
        if uf in UFS:
            return uf

    # fallback comum GNRE: "DF 100102"
    m = re.search(r"\b([A-Z]{2})\b\s+100102\b", texto, flags=re.I | re.S)
    if m:
        uf = m.group(1).upper()
        if uf in UFS:
            return uf

    return None

def _extrair_vencimento(texto: str) -> str | None:
    m = re.search(r"Data\s*de\s*Vencimento.*?(\d{2}/\d{2}/\d{4})", texto, flags=re.I | re.S)
    if m:
        return m.group(1)

    m = re.search(r"Vencimento.*?(\d{2}/\d{2}/\d{4})", texto, flags=re.I | re.S)
    return m.group(1) if m else None

def _extrair_valor(texto: str) -> str | None:
    m = re.search(r"Total\s*a\s*Recolher.*?R?\$?\s*([\d\.]+,\d{2})", texto, flags=re.I | re.S)
    if m:
        return m.group(1)

    m = re.search(r"Total\s*a\s*Recolher.*?([\d\.]+,\d{2})", texto, flags=re.I | re.S)
    return m.group(1) if m else None

def _snippet(texto: str, label: str, width: int = 160) -> str | None:
    """
    Pega um trecho do texto logo após um rótulo (se existir) pra debug.
    """
    t = texto or ""
    idx = t.lower().find(label.lower())
    if idx == -1:
        return None
    return t[idx: idx + width].replace("\n", "\\n")

def extrair_gnres_do_pdf_com_debug(pdf_path: str):
    """
    Retorna (ok, falhas)
    ok: lista de guias completas para CNAB
    falhas: lista com páginas e campos faltantes + trechos
    """
    ok = []
    falhas = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""

            linha = _extrair_linha_digitavel_unica(texto)
            uf = _extrair_uf_favorecida(texto)
            venc = _extrair_vencimento(texto)
            valor = _extrair_valor(texto)

            faltando = []
            if not linha: faltando.append("linha_digitavel")
            if not uf: faltando.append("uf")
            if not venc: faltando.append("vencimento")
            if not valor: faltando.append("valor")

            if not faltando:
                ok.append({
                    "pagina": i,
                    "uf": uf,
                    "vencimento": venc,
                    "valor": valor,
                    "linha_digitavel": linha,
                })
            else:
                falhas.append({
                    "pagina": i,
                    "faltando": ", ".join(faltando),
                    "linha_digitavel": (linha[:22] + "...") if linha else None,
                    "uf": uf,
                    "vencimento": venc,
                    "valor": valor,
                    "snip_uf": _snippet(texto, "UF Favorecida"),
                    "snip_venc": _snippet(texto, "Data de Vencimento"),
                    "snip_valor": _snippet(texto, "Total a Recolher"),
                })

    return ok, falhas

def extrair_gnres_do_pdf(pdf_path: str):
    """
    Mantém compatibilidade com o app antigo:
    retorna apenas as completas.
    """
    ok, _ = extrair_gnres_do_pdf_com_debug(pdf_path)
    return ok
