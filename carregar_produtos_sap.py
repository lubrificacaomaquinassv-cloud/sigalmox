#!/usr/bin/env python3
"""
Importa Excel SAP para SIGALMOX (produtos + snapshot estoque).

Uso:
  python carregar_produtos_sap.py lista.xlsx --categoria "Medicamentos Pecuária"
  python carregar_produtos_sap.py lista.xlsx --categoria "Filtros" --gerar-pdf

Requer .streamlit/secrets.toml com credenciais Supabase.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parent
SECRETS = ROOT / ".streamlit" / "secrets.toml"

COL_ALIASES = {
    "codigo": {"codigo", "código", "cod", "cód", "sap", "material", "item"},
    "descricao": {"descricao", "descrição", "produto", "texto breve material", "denominação"},
    "em_estoque": {"em_estoque", "estoque", "qtd_sap", "quantidade", "saldo", "livre utilização"},
}

CATEGORIAS_INTERNAS = {
    "Medicamentos Pecuária", "Vacinas e Inseminação", "Filtros",
    "Defensivos Agrícola", "Carvão Vegetal", "Gás de Cozinha",
    "Consumíveis Manutenção", "Consumíveis Borracharia",
}


def normalizar_coluna(nome: str) -> str:
    txt = str(nome).strip().lower()
    while "  " in txt:
        txt = txt.replace("  ", " ")
    return txt


def ler_excel(caminho: Path) -> pd.DataFrame:
    df = pd.read_excel(caminho)
    col_map = {}
    for col in df.columns:
        norm = normalizar_coluna(col)
        for destino, aliases in COL_ALIASES.items():
            if norm in aliases and destino not in col_map:
                col_map[destino] = col
    if {"codigo", "descricao", "em_estoque"}.issubset(col_map):
        out = pd.DataFrame({
            "codigo": df[col_map["codigo"]],
            "descricao": df[col_map["descricao"]],
            "em_estoque": df[col_map["em_estoque"]],
        })
    elif len(df.columns) >= 3:
        out = df.iloc[:, :3].copy()
        out.columns = ["codigo", "descricao", "em_estoque"]
    else:
        raise ValueError("Excel precisa ter: codigo, descricao, em_estoque")
    out["codigo"] = out["codigo"].astype(str).str.strip()
    out["descricao"] = out["descricao"].astype(str).str.strip()
    out["em_estoque"] = pd.to_numeric(out["em_estoque"], errors="coerce").fillna(0)
    out = out[(out["codigo"] != "") & (out["codigo"].str.lower() != "nan")]
    return out


def load_db_cfg():
    if not SECRETS.is_file():
        print(f"Secrets não encontrado: {SECRETS}", file=sys.stderr)
        sys.exit(1)
    with open(SECRETS, "rb") as f:
        data = tomllib.load(f)
    if "connections" in data and "supabase" in data["connections"]:
        return data["connections"]["supabase"]
    return {
        "host": "aws-1-sa-east-1.pooler.supabase.com",
        "port": 6543,
        "database": "postgres",
        "username": f"postgres.{data.get('SUPABASE_URL', '').split('.')[0].split('//')[-1]}",
        "password": data.get("DB_PASSWORD", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Carrega produtos SAP no SIGALMOX")
    parser.add_argument("excel", type=Path)
    parser.add_argument("--categoria", default="Medicamentos Pecuária")
    parser.add_argument("--gerar-pdf", action="store_true")
    parser.add_argument("--saida-pdf", type=Path, default=None)
    args = parser.parse_args()

    if not args.excel.is_file():
        print(f"Arquivo não encontrado: {args.excel}", file=sys.stderr)
        sys.exit(1)

    df = ler_excel(args.excel)
    if df.empty:
        print("Excel vazio.", file=sys.stderr)
        sys.exit(1)

    cfg = load_db_cfg()
    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], database=cfg["database"],
        user=cfg["username"], password=cfg["password"], sslmode="require",
    )
    cur = conn.cursor()

    local_tipo = "interno" if args.categoria in CATEGORIAS_INTERNAS else "externo"

    cur.execute(
        "INSERT INTO almoxarifado.sap_importacao (arquivo_nome, categoria, total_itens) "
        "VALUES (%s, %s, %s) RETURNING id",
        (args.excel.name, args.categoria, len(df)),
    )
    importacao_id = cur.fetchone()[0]

    cur.execute("SELECT codigo_sap, id FROM almoxarifado.produtos")
    existentes = {r[0]: r[1] for r in cur.fetchall()}
    novos = atualizados = 0

    for _, row in df.iterrows():
        codigo = str(row["codigo"]).strip()
        descricao = str(row["descricao"]).strip()
        qtd = float(row["em_estoque"])

        cur.execute(
            "INSERT INTO almoxarifado.sap_estoque_importado "
            "(importacao_id, codigo_sap, descricao, qtd_sap, categoria) VALUES (%s,%s,%s,%s,%s)",
            (importacao_id, codigo, descricao, qtd, args.categoria),
        )

        qr_code = f"SIGALMOX-{codigo}"
        if codigo not in existentes:
            cur.execute(
                "INSERT INTO almoxarifado.produtos "
                "(codigo_sap, qr_code, descricao, categoria, local_tipo, estoque_atual) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (codigo, qr_code, descricao, args.categoria, local_tipo, qtd),
            )
            novos += 1
        else:
            cur.execute(
                "UPDATE almoxarifado.produtos SET descricao=%s, categoria=%s, updated_at=NOW() "
                "WHERE codigo_sap=%s",
                (descricao, args.categoria, codigo),
            )
            atualizados += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"Importação concluída: {len(df)} itens ({novos} novos, {atualizados} existentes)")
    print(f"Importação ID: {importacao_id}")

    if args.gerar_pdf:
        from gerar_qr_etiquetas import _gerar_pdf
        saida = args.saida_pdf or args.excel.with_name(f"etiquetas_sigalmox_{args.excel.stem}.pdf")
        with open(saida, "wb") as f:
            _gerar_pdf(df, f, args.categoria, args.categoria)
        print(f"PDF gerado: {saida}")


if __name__ == "__main__":
    main()
