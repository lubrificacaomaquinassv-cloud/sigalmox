# SIGALMOX — Controle de Estoque · Santa Virgínia

Sistema de baixa de estoque por retirada física (scan QR), conciliação com SAP.

## Componentes

| Componente | Arquivo | Uso |
|------------|---------|-----|
| Painel Streamlit | `sigalmox_app.py` | Mesa de trabalho — entrada, conciliação, pendências SAP |
| PWA celular | `pwa-sigalmox/` | Scan QR na prateleira |
| Schema SQL | `sql/001_almoxarifado_schema.sql` | Banco Supabase (schema `almoxarifado`) |
| Import SAP | `carregar_produtos_sap.py` | CLI — Excel → produtos + QR |

## Deploy

- **Streamlit Cloud:** `sigalmox_app.py` — ver `LEIA-ME.txt`
- **PWA GitHub Pages:** `PUBLICAR_PWA.bat` → `/painel-frota-sv/almox/`

## Fluxo

```
Scan QR → retirada SIGALMOX → baixa SAP (manual) → ✅ Pendências SAP → Conciliação
```

Detalhes operacionais: `LEIA-ME.txt`
