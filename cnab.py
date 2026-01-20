from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from pathlib import Path
import re

# =============================
# DADOS FIXOS DO PAGADOR
# =============================
BANK = "341"
CNPJ = "03781919000158"
AG = "1529"
CONTA = "70940"
DAC = "2"
EMPRESA = "FASM COMERCIO DE ARTIGOS DO VESTUARIO LTDA"

# =============================
# HELPERS
# =============================
def pad_right(s, n, ch=" "):
    s = "" if s is None else str(s)
    if len(s) > n:
        s = s[:n]
    return s + ch * (n - len(s))

def pad_left(s, n, ch="0"):
    s = "" if s is None else str(s)
    if len(s) > n:
        s = s[-n:]
    return ch * (n - len(s)) + s

def only_digits(s):
    return re.sub(r"\D", "", str(s or ""))

def parse_brl_to_cents(v):
    s = str(v).strip().replace("R$", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    d = Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))

def ddmmaaaa(date_str):
    d, m, y = date_str.strip().split("/")
    return f"{d}{m}{y}"

# =============================
# CONTADOR DE NOME DO ARQUIVO
# =============================
def proximo_nome_cnab(seq_file: Path) -> str:
    if seq_file.exists():
        n = int(seq_file.read_text(encoding="utf-8").strip() or "0")
    else:
        n = 0
    n += 1
    seq_file.write_text(str(n), encoding="utf-8")
    return f"CNAB{n:04d}"  # exatamente 8 caracteres

# =============================
# FUNÇÃO PRINCIPAL (IMPORTADA)
# =============================
def gerar_cnab_itau_gnre_segmento_o(gnres: list[dict], nome_base_8chars: str) -> bytes:
    """
    gnres: [{uf, linha_digitavel, valor, vencimento}]
    retorna bytes do arquivo CNAB240
    """

    if len(nome_base_8chars) != 8:
        raise ValueError("Nome base do arquivo deve ter exatamente 8 caracteres (ex: CNAB0001).")

    # Datas
    now = datetime.now()
    data_geracao = now.strftime("%d%m%Y")
    hora_geracao = now.strftime("%H%M%S")
    data_pagto = ddmmaaaa(gnres[0]["vencimento"])

    empresa_30 = pad_right(EMPRESA, 30)
    banco_nome_30 = pad_right("BANCO ITAU S.A.", 30)

    # ================= HEADER ARQUIVO =================
    hdr = (
        pad_left(BANK,3) + "0000" + "0" + pad_right("",6) + "080" + "2" +
        pad_left(CNPJ,14) + pad_right("",20) +
        pad_left(AG,5) + " " + pad_left(CONTA,12) + " " + pad_left(DAC,1) +
        empresa_30 + banco_nome_30 +
        pad_right("",10) + "1" + data_geracao + hora_geracao +
        pad_left("0",9) + pad_left("0",5) + pad_right("",69)
    )
    assert len(hdr) == 240

    # ================= HEADER LOTE =================
    seq_lote = 1
    hdr_lote = (
        pad_left(BANK,3) + pad_left(seq_lote,4) + "1" +
        "C" + "22" + "91" + "040" + " " + "2" +
        pad_left(CNPJ,14) +
        pad_right("",4) + pad_right("",16) +
        pad_left(AG,5) + " " + pad_left(CONTA,12) + " " + pad_left(DAC,1) +
        empresa_30 +
        pad_right("",30) + pad_right("",10) +
        pad_right("",30) + pad_left("0",5) + pad_right("",15) +
        pad_right("",20) + pad_left("0",8) + pad_right("",2) +
        pad_right("",8) + pad_right("",10)
    )
    assert len(hdr_lote) == 240

    # ================= SEGMENTOS O =================
    segmentos = []
    total_cent = 0

    for idx, g in enumerate(gnres, start=1):
        codigo = only_digits(g["linha_digitavel"])
        if len(codigo) == 49:
            codigo = codigo[:48]
        if len(codigo) != 48:
            raise ValueError(f"GNRE {idx}: código de barras inválido ({len(codigo)} dígitos)")

        valor_cent = parse_brl_to_cents(g["valor"])
        total_cent += valor_cent
        venc = ddmmaaaa(g["vencimento"])

        segO = (
            pad_left(BANK,3) + pad_left(seq_lote,4) + "3" +
            pad_left(idx,5) + "O" + "000" +
            pad_right(codigo,48) +
            pad_right(f"GNRE {g['uf']}",30) +
            venc + "REA" +
            pad_left("0",15) +
            pad_left(valor_cent,15) +
            data_pagto +
            pad_left("0",15) +
            pad_right("",3) +
            pad_left("0",9) +
            pad_right("",3) +
            pad_right(f"GNRE-{g['uf']}-{venc}-{idx:05d}",20) +
            pad_right("",21) +
            pad_right("",15) +
            pad_right("",10)
        )
        assert len(segO) == 240
        segmentos.append(segO)

    # ================= TRAILER LOTE =================
    qtd_reg_lote = 1 + len(segmentos) + 1
    trl_lote = (
        pad_left(BANK,3) + pad_left(seq_lote,4) + "5" +
        pad_right("",9) +
        pad_left(qtd_reg_lote,6) +
        pad_left(total_cent,18) +
        pad_left("0",18) +
        pad_right("",171) +
        pad_right("",10)
    )
    assert len(trl_lote) == 240

    # ================= TRAILER ARQUIVO =================
    total_regs = 1 + 1 + len(segmentos) + 1 + 1
    trl_arq = (
        pad_left(BANK,3) + "9999" + "9" +
        pad_right("",9) +
        pad_left(1,6) +
        pad_left(total_regs,6) +
        pad_right("",211)
    )
    assert len(trl_arq) == 240

    # ================= MONTA ARQUIVO =================
    linhas = [hdr, hdr_lote] + segmentos + [trl_lote, trl_arq]
    conteudo = "".join(l + "\r\n" for l in linhas)
    return conteudo.encode("ascii", errors="ignore")
