#!/usr/bin/env python3
"""Aplica sql/001_almoxarifado_schema.sql no Supabase (uma vez)."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

import psycopg2

ROOT = Path(__file__).resolve().parent
SQL_FILE = ROOT / "sql" / "001_almoxarifado_schema.sql"
SECRETS_LOCAL = ROOT / ".streamlit" / "secrets.toml"
SECRETS_SHARED = ROOT.parent.parent / "pwa-comboio-posto-abastecimento" / "requisicao-compras" / ".streamlit" / "secrets.toml"


def load_db_cfg():
    for path in (SECRETS_LOCAL, SECRETS_SHARED):
        if path.is_file():
            with open(path, "rb") as f:
                data = tomllib.load(f)
            if "connections" in data and "supabase" in data["connections"]:
                return data["connections"]["supabase"]
    print("Secrets não encontrado. Cole sql/001_almoxarifado_schema.sql no Supabase SQL Editor.")
    sys.exit(1)


def main():
    if not SQL_FILE.is_file():
        print(f"SQL não encontrado: {SQL_FILE}")
        sys.exit(1)
    sql = SQL_FILE.read_text(encoding="utf-8")
    cfg = load_db_cfg()
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
        user=cfg["username"],
        password=cfg["password"],
        sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.close()
    print("OK — schema almoxarifado aplicado.")
    print("Lembre: Settings > API > Exposed schemas > adicionar 'almoxarifado'")


if __name__ == "__main__":
    main()
