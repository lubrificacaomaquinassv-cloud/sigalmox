#!/usr/bin/env python3
"""
Gera PDF de etiquetas QR para SIGALMOX.
Formato QR: SIGALMOX-{codigo_sap}

Uso:
  python gerar_qr_etiquetas.py lista.xlsx --categoria "Medicamentos Pecuária"
  python gerar_qr_etiquetas.py lista.xlsx --saida etiquetas.pdf
"""
from __future__ import annotations

import argparse
import io
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def qr_png(payload: str, box_size: int = 4) -> bytes:
    img = qrcode.make(str(payload).strip(), box_size=box_size, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def truncar(texto: str, max_len: int = 38) -> str:
    t = str(texto or "").strip()
    return t if len(t) <= max_len else t[: max_len - 1] + "…"


def gerar_pdf_bytes(df: pd.DataFrame, categoria: str, setor: str = "") -> bytes:
    """Retorna bytes do PDF (para Streamlit download)."""
    buf = io.BytesIO()
    _gerar_pdf(df, buf, categoria, setor or categoria)
    return buf.getvalue()


def _gerar_pdf(df: pd.DataFrame, saida, categoria: str, setor: str) -> None:
    largura, altura = A4
    margem = 12 * mm
    linha_h = 26 * mm
    c = canvas.Canvas(saida, pagesize=A4)

    def cabecalho(pag: int, total: int):
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#1a2818"))
        c.drawString(margem, altura - margem, f"SIGALMOX — {setor}")
        c.setFont("Helvetica", 8)
        c.drawString(margem, altura - margem - 12, f"{categoria} · {date.today():%d/%m/%Y}")
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.grey)
        c.drawRightString(largura - margem, altura - margem, f"Pág {pag}/{total}")
        c.setStrokeColor(colors.HexColor("#4a6644"))
        c.line(margem, altura - margem - 16, largura - margem, altura - margem - 16)

    itens_por_pag = int((altura - 2 * margem - 28 * mm) // linha_h)
    paginas = max(1, (len(df) + itens_por_pag - 1) // itens_por_pag)
    idx = 0

    for pag in range(1, paginas + 1):
        cabecalho(pag, paginas)
        y = altura - margem - 26 * mm
        for _ in range(itens_por_pag):
            if idx >= len(df):
                break
            row = df.iloc[idx]
            codigo = str(row.get("codigo", row.get("codigo_sap", ""))).strip()
            desc = truncar(str(row.get("descricao", "")))
            qr_payload = f"SIGALMOX-{codigo}"

            qr_size = 20 * mm
            c.drawImage(
                ImageReader(io.BytesIO(qr_png(qr_payload))),
                largura - margem - qr_size,
                y - qr_size + 3 * mm,
                width=qr_size, height=qr_size, mask="auto",
            )
            c.setFillColor(colors.HexColor("#1a2818"))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margem, y, f"SAP {codigo}")
            c.setFont("Helvetica", 8)
            c.drawString(margem, y - 10, desc)
            c.setFont("Helvetica", 6)
            c.setFillColor(colors.HexColor("#4a6644"))
            c.drawString(margem, y - 18, qr_payload)
            c.setStrokeColor(colors.HexColor("#dce6d2"))
            c.line(margem, y - 22, largura - margem, y - 22)
            y -= linha_h
            idx += 1
        c.showPage()
    c.save()


def ler_excel(caminho: Path) -> pd.DataFrame:
    df = pd.read_excel(caminho)
    if len(df.columns) >= 3:
        df = df.iloc[:, :3].copy()
        df.columns = ["codigo", "descricao", "em_estoque"]
    df["codigo"] = df["codigo"].astype(str).str.strip()
    return df


def main():
    parser = argparse.ArgumentParser(description="Gera etiquetas QR SIGALMOX")
    parser.add_argument("excel", type=Path)
    parser.add_argument("--categoria", default="Almoxarifado")
    parser.add_argument("--saida", type=Path, default=None)
    args = parser.parse_args()
    if not args.excel.is_file():
        print(f"Arquivo não encontrado: {args.excel}", file=sys.stderr)
        sys.exit(1)
    df = ler_excel(args.excel)
    saida = args.saida or args.excel.with_name(f"etiquetas_sigalmox_{args.excel.stem}.pdf")
    with open(saida, "wb") as f:
        _gerar_pdf(df, f, args.categoria, args.categoria)
    print(f"PDF gerado: {saida} ({len(df)} etiquetas)")


if __name__ == "__main__":
    main()
