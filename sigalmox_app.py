import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

from supabase import create_client, Client
from sigcf_auth import exigir_acesso, logo_html

st.set_page_config(
    page_title="SIGALMOX — SANTA VERGÍNIA",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCHEMA = "almoxarifado"
BG_URL = "https://media.bio.site/sites/32a25c2c-d6fa-4dfc-bdc2-27e4d35d7ea2/AhS9mKiQxFRXAyMBdXDzEG.jpg"

CATEGORIAS_INTERNAS = [
    "Medicamentos Pecuária", "Vacinas e Inseminação", "Filtros",
    "Defensivos Agrícola", "Carvão Vegetal", "Gás de Cozinha",
    "Consumíveis Manutenção", "Consumíveis Borracharia",
]
CATEGORIAS_EXTERNAS = [
    "Lubrificantes", "Adubos e Fertilizantes", "Combustíveis",
    "Nutrição Animal", "EPIs", "Viveiro Floresta", "SESTR",
]
CATEGORIAS_CRITICAS = [
    "Medicamentos Pecuária", "Nutrição Animal", "Lubrificantes",
    "Combustíveis", "Defensivos Agrícola", "Filtros",
]
TODAS_CATEGORIAS = CATEGORIAS_INTERNAS + CATEGORIAS_EXTERNAS

COL_ALIASES = {
    "codigo": {"codigo", "código", "cod", "cód", "sap", "material", "item"},
    "descricao": {"descricao", "descrição", "produto", "texto breve material", "denominação"},
    "em_estoque": {"em_estoque", "estoque", "qtd_sap", "quantidade", "saldo", "livre utilização"},
    "disponivel": {"disponivel", "disponível", "qtd_disponivel", "saldo_disponivel"},
}

exigir_acesso("SIGALMOX — SANTA VERGÍNIA", "Controle de estoque — conciliação com SAP")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');
.stApp{
 background:linear-gradient(rgba(10,20,9,0.68),rgba(10,20,9,0.82)),
 url('__BG__') center center/cover no-repeat fixed!important;}
[data-testid="stAppViewContainer"]{background:transparent!important;}
[data-testid="stSidebar"]{display:none;}
[data-testid="stHeader"]{background:rgba(10,20,9,0.45)!important;}
.block-container{background:transparent!important;max-width:1100px!important;}
h1,h2,h3,h4,p,span,label{color:#e8edd0;}
h1{font-family:'Barlow Condensed',sans-serif;letter-spacing:1px;}
.stCaption,[data-testid="stCaptionContainer"] p{color:#9ab892!important;}
.sec{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;
 letter-spacing:2px;text-transform:uppercase;color:#9ab892;
 border-left:4px solid #5a9452;padding-left:10px;margin:8px 0 12px;}
.logo-frame{background:linear-gradient(145deg,#0a1628,#0d2040);border:2px solid #c9a227;
 border-radius:12px;padding:5px;display:inline-block;box-shadow:0 4px 18px rgba(0,0,0,.45);}
.logo-frame img{display:block;border-radius:8px;}
.ctx-box{background:rgba(13,24,12,0.88);border:1px solid #2a3d28;border-radius:12px;padding:14px 16px;margin-bottom:12px;}
.hub-card{background:rgba(17,28,16,0.86);border:1px solid #2a3d28;border-radius:14px;padding:18px 14px;
 text-align:center;min-height:118px;transition:border-color .2s;}
.hub-card.active{border-color:rgba(90,148,82,0.85);border-top:3px solid #5a9452;}
.hub-card.soon{opacity:.55;border-style:dashed;}
.hub-card .ico{font-size:28px;line-height:1;margin-bottom:8px;}
.hub-card .tit{font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;
 color:#e8edd0;text-transform:uppercase;letter-spacing:.5px;line-height:1.25;}
.hub-card .tag{font-size:9px;font-weight:700;letter-spacing:1px;margin-top:8px;
 display:inline-block;padding:3px 10px;border-radius:10px;}
.hub-card.active .tag{background:rgba(26,58,24,0.9);color:#8ec486;border:1px solid #5a9452;}
.hub-card.soon .tag{background:#1a1a10;color:#8aab80;border:1px solid #3a4a38;}
.badge-critico{background:#5c1a1a;color:#ff8888;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;}
.badge-atencao{background:#4a3a10;color:#ffd080;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;}
.badge-ok{background:#1a3a1a;color:#8ec486;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;}
.insta-link{display:inline-flex;align-items:center;gap:6px;color:#8ec486!important;
 text-decoration:none;font-weight:600;}
.stTextInput input,.stNumberInput input,.stTextArea textarea,
[data-testid="stDateInput"] input{
 background:#dce6d2!important;color:#1a2818!important;
 border:1px solid #4a6644!important;border-radius:8px!important;}
div[data-baseweb="select"] > div{
 background:#dce6d2!important;border:1px solid #4a6644!important;
 color:#1a2818!important;border-radius:8px!important;}
[data-testid="stForm"]{
 background:rgba(13,24,12,0.88)!important;border:1px solid #2a3d28!important;
 border-radius:12px;padding:12px 16px;}
div[data-testid="stMetric"]{background:rgba(13,24,12,0.88);border:1px solid #2a3d28;border-radius:10px;padding:10px 14px;}
div[data-testid="stMetric"] label{color:#9ab892!important;}
div[data-testid="stMetricValue"]{color:#8ec486!important;font-family:'Barlow Condensed',sans-serif;}
.stTabs [data-baseweb="tab-list"]{background:rgba(13,24,12,0.88);border-bottom:1px solid #2a3d28;gap:8px;}
.stTabs [data-baseweb="tab"]{
 color:#9ab892!important;font-family:'Barlow Condensed',sans-serif;font-weight:600;}
.stTabs [aria-selected="true"]{color:#e8edd0!important;border-bottom-color:#5a9452!important;}
.stTabs [data-baseweb="tab-highlight"]{background-color:#5a9452!important;}
.stButton button,[data-testid="stFormSubmitButton"] button{
 background:#4a9e3f!important;color:#ffffff!important;border:1px solid #6fa864!important;
 font-family:'Barlow Condensed',sans-serif;font-weight:700;letter-spacing:1.5px;
 text-transform:uppercase;border-radius:8px;min-height:44px;}
.stButton button:hover,[data-testid="stFormSubmitButton"] button:hover{background:#3d8534!important;}
@media (max-width:768px){
 .block-container{padding-left:0.75rem!important;padding-right:0.75rem!important;}
 div[data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;}
}
</style>
""".replace("__BG__", BG_URL), unsafe_allow_html=True)


def link_instagram(text: str = "@fazendasantaverginia") -> str:
    icon = (
        '<img class="insta-ico" src="https://cdn.simpleicons.org/instagram/8ec486" '
        'width="17" height="17" alt="" loading="lazy">'
    )
    return (
        f'<a class="insta-link" href="https://www.instagram.com/fazendasantaverginia" '
        f'target="_blank" rel="noopener">{icon}{text}</a>'
    )


def dark_table(df: pd.DataFrame, height: int = 320):
    if df.empty:
        st.info("Nenhum registro.")
        return
    rows = "".join(
        "<tr>" + "".join(
            f'<td style="padding:6px 10px;border-bottom:1px solid #1e2e1c;'
            f'color:#e8edd0;font-size:12px;">{v}</td>'
            for v in row) + "</tr>"
        for _, row in df.iterrows())
    headers = "".join(
        f'<th style="padding:7px 10px;background:#111c10;color:#8aab80;font-size:10px;'
        f'font-weight:700;text-transform:uppercase;letter-spacing:1px;'
        f'border-bottom:2px solid #1e2e1c;">{c}</th>'
        for c in df.columns)
    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid #1e2e1c;border-radius:10px;">'
        f'<div style="max-height:{height}px;overflow-y:auto;">'
        f'<table style="width:100%;border-collapse:collapse;background:#0d180c;'
        f'font-family:Barlow Condensed,sans-serif;"><thead><tr>{headers}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div></div>',
        unsafe_allow_html=True,
    )


def gerar_excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def fmt_data(d) -> str:
    if not d:
        return ""
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(d)[:16].replace("T", " ")


def fmt_num(n) -> str:
    try:
        return f"{float(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(n)


def ler_credenciais_supabase() -> tuple[str, str]:
    url = (
        st.secrets.get("SUPABASE_URL")
        or st.secrets.get("supabase_url")
        or (st.secrets.get("supabase", {}) or {}).get("url")
    )
    key = (
        st.secrets.get("SUPABASE_KEY")
        or st.secrets.get("supabase_key")
        or (st.secrets.get("supabase", {}) or {}).get("key")
    )
    return str(url or "").strip(), str(key or "").strip()


def criar_sb(url: str, key: str) -> Client:
    return create_client(url, key)


def tbl(sb: Client, nome: str):
    """Sempre usa schema almoxarifado explicitamente."""
    return sb.schema(SCHEMA).from_(nome)


def tbl_view(sb: Client, nome: str):
    return sb.schema(SCHEMA).from_(nome)


def testar_conexao_rest(url: str, key: str) -> tuple[bool, str]:
    """Teste direto via REST (Accept-Profile) — mais confiável que supabase-py."""
    import json
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    req_url = f"{url.rstrip('/')}/rest/v1/destinos?select=id&limit=1"
    req = Request(
        req_url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept-Profile": SCHEMA,
        },
    )
    try:
        with urlopen(req, timeout=12) as resp:
            json.loads(resp.read().decode())
        return True, ""
    except HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def testar_conexao(url: str, key: str) -> tuple[bool, str]:
    ok, msg = testar_conexao_rest(url, key)
    if ok:
        return True, ""
    try:
        sb = criar_sb(url, key)
        tbl(sb, "destinos").select("id").limit(1).execute()
        return True, ""
    except Exception as e:
        return False, msg or str(e)


def executar_consulta(fn, padrao=None):
    """Executa consulta Supabase sem derrubar o app."""
    try:
        return fn()
    except Exception as e:
        msg = str(e)
        if "PGRST106" in msg:
            st.session_state["sb_erro"] = (
                "PostgREST não reconhece o schema almoxarifado. "
                "Rode o SQL de reload no Supabase e clique **Atualizar**."
            )
        elif "42501" in msg:
            st.session_state["sb_erro"] = "Sem permissão no schema almoxarifado. Rode sql/002_reload_postgrest_schema.sql."
        elif "Invalid API key" in msg or "401" in msg or "JWT" in msg:
            st.session_state["sb_erro"] = "SUPABASE_KEY inválida nos Secrets do Streamlit Cloud."
        else:
            st.session_state["sb_erro"] = f"Erro ao consultar banco: {msg[:220]}"
        return padrao if padrao is not None else []


def normalizar_coluna(nome: str) -> str:
    txt = str(nome).strip().lower()
    while "  " in txt:
        txt = txt.replace("  ", " ")
    return txt


def ler_excel_sap(uploaded) -> pd.DataFrame:
    df = pd.read_excel(uploaded)
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
        raise ValueError("Excel precisa ter: código, descrição e estoque")
    out["codigo"] = out["codigo"].astype(str).str.strip()
    out["descricao"] = out["descricao"].astype(str).str.strip()
    out["em_estoque"] = pd.to_numeric(out["em_estoque"], errors="coerce").fillna(0)
    out = out[(out["codigo"] != "") & (out["codigo"].str.lower() != "nan")]
    return out


def _enriquecer_movimentacoes(sb: Client, rows: list) -> list:
    if not rows:
        return rows
    prod_ids = list({r["produto_id"] for r in rows if r.get("produto_id")})
    if not prod_ids:
        return rows
    prods = (
        tbl(sb, "produtos").select("id, codigo_sap, descricao, categoria")
        .in_("id", prod_ids).execute().data or []
    )
    pmap = {p["id"]: p for p in prods}
    for r in rows:
        r["produtos"] = pmap.get(r.get("produto_id"), {})
    return rows


@st.cache_data(ttl=30)
def carregar_produtos(_sb_url: str, _sb_key: str, categoria: str | None = None) -> list:
    sb = criar_sb(_sb_url, _sb_key)
    q = tbl(sb, "produtos").select("*").eq("ativo", True).order("descricao")
    if categoria:
        q = q.eq("categoria", categoria)
    return executar_consulta(lambda: q.execute().data or [])


@st.cache_data(ttl=30)
def carregar_destinos(_sb_url: str, _sb_key: str) -> list:
    sb = criar_sb(_sb_url, _sb_key)
    return executar_consulta(
        lambda: tbl(sb, "destinos").select("*").eq("ativo", True).order("nome").execute().data or []
    )


@st.cache_data(ttl=30)
def carregar_responsaveis(_sb_url: str, _sb_key: str) -> list:
    sb = criar_sb(_sb_url, _sb_key)
    return executar_consulta(
        lambda: tbl(sb, "responsaveis").select("*").eq("ativo", True).order("nome").execute().data or []
    )


@st.cache_data(ttl=15)
def carregar_pendencias(_sb_url: str, _sb_key: str) -> list:
    sb = criar_sb(_sb_url, _sb_key)

    def _load():
        rows = (
            tbl(sb, "movimentacoes").select("*")
            .eq("baixado_sap", False)
            .order("data_retirada", desc=True)
            .execute().data or []
        )
        return _enriquecer_movimentacoes(sb, rows)

    return executar_consulta(_load)


@st.cache_data(ttl=15)
def carregar_movimentacoes_dia(_sb_url: str, _sb_key: str, dia: str) -> list:
    sb = criar_sb(_sb_url, _sb_key)
    ini = f"{dia}T00:00:00"
    fim = f"{dia}T23:59:59"

    def _load():
        rows = (
            tbl(sb, "movimentacoes").select("*")
            .gte("data_retirada", ini).lte("data_retirada", fim)
            .order("data_retirada", desc=True)
            .execute().data or []
        )
        return _enriquecer_movimentacoes(sb, rows)

    return executar_consulta(_load)


@st.cache_data(ttl=30)
def carregar_estoques_criticos(_sb_url: str, _sb_key: str) -> list:
    sb = criar_sb(_sb_url, _sb_key)

    def _load():
        try:
            return tbl_view(sb, "v_estoques_criticos").select("*").execute().data or []
        except Exception:
            produtos = carregar_produtos(_sb_url, _sb_key)
            return [p for p in produtos if p.get("categoria") in CATEGORIAS_CRITICAS]

    return executar_consulta(_load)


@st.cache_data(ttl=30)
def carregar_ultima_importacao(_sb_url: str, _sb_key: str, categoria: str) -> dict | None:
    sb = criar_sb(_sb_url, _sb_key)

    def _load():
        rows = (
            tbl(sb, "sap_importacao").select("*")
            .eq("categoria", categoria)
            .order("importado_em", desc=True)
            .limit(1).execute().data or []
        )
        return rows[0] if rows else None

    return executar_consulta(_load, padrao=None)


@st.cache_data(ttl=30)
def carregar_sap_importado(_sb_url: str, _sb_key: str, importacao_id: str) -> list:
    sb = criar_sb(_sb_url, _sb_key)
    return executar_consulta(
        lambda: tbl(sb, "sap_estoque_importado").select("*")
        .eq("importacao_id", importacao_id).execute().data or []
    )


def importar_produtos_sap(sb: Client, df: pd.DataFrame, categoria: str, arquivo_nome: str) -> dict:
    """Importa Excel SAP: cadastra produtos novos, atualiza estoque, gera snapshot."""
    imp = tbl(sb, "sap_importacao").insert({
        "arquivo_nome": arquivo_nome,
        "categoria": categoria,
        "total_itens": len(df),
    }).execute()
    importacao_id = imp.data[0]["id"]

    existentes = {
        p["codigo_sap"]: p
        for p in (tbl(sb, "produtos").select("*").execute().data or [])
    }

    novos = 0
    atualizados = 0
    local_tipo = "interno" if categoria in CATEGORIAS_INTERNAS else "externo"

    for _, row in df.iterrows():
        codigo = str(row["codigo"]).strip()
        descricao = str(row["descricao"]).strip()
        qtd_sap = float(row["em_estoque"])

        tbl(sb, "sap_estoque_importado").insert({
            "importacao_id": importacao_id,
            "codigo_sap": codigo,
            "descricao": descricao,
            "qtd_sap": qtd_sap,
            "categoria": categoria,
        }).execute()

        qr_code = f"SIGALMOX-{codigo}"
        if codigo not in existentes:
            tbl(sb, "produtos").insert({
                "codigo_sap": codigo,
                "qr_code": qr_code,
                "descricao": descricao,
                "categoria": categoria,
                "local_tipo": local_tipo,
                "estoque_atual": qtd_sap,
            }).execute()
            novos += 1
        else:
            tbl(sb, "produtos").update({
                "descricao": descricao,
                "categoria": categoria,
            }).eq("codigo_sap", codigo).execute()
            atualizados += 1

    return {"importacao_id": importacao_id, "novos": novos, "atualizados": atualizados, "total": len(df)}


def calcular_conciliacao(
    produtos: list, sap_itens: list, movimentacoes_pendentes: list
) -> pd.DataFrame:
    """Cruzamento SIGALMOX × SAP em memória (fallback se view indisponível)."""
    prod_map = {p["codigo_sap"]: p for p in produtos}
    sap_map = {s["codigo_sap"]: s for s in sap_itens}
    pend_map: dict[str, float] = {}
    for m in movimentacoes_pendentes:
        cod = (m.get("produtos") or {}).get("codigo_sap", "")
        if cod:
            pend_map[cod] = pend_map.get(cod, 0) + float(m["quantidade"])

    codigos = set(prod_map) | set(sap_map)
    rows = []
    for cod in sorted(codigos):
        p = prod_map.get(cod, {})
        s = sap_map.get(cod, {})
        est_sig = float(p.get("estoque_atual", 0) or 0)
        est_sap = float(s.get("qtd_sap", 0) or 0)
        pend = pend_map.get(cod, 0)
        div = est_sig - est_sap
        if cod not in sap_map:
            status = "SEM_SAP"
        elif cod not in prod_map:
            status = "SEM_SIGALMOX"
        elif pend > 0:
            status = "BAIXA_PENDENTE_SAP"
        elif abs(div) <= 0.001:
            status = "OK"
        elif abs(div) <= 1:
            status = "DIVERGENCIA_LEVE"
        else:
            status = "DIVERGENCIA_REAL"
        rows.append({
            "Código SAP": cod,
            "Descrição": p.get("descricao") or s.get("descricao", ""),
            "Categoria": p.get("categoria") or s.get("categoria", ""),
            "Estoque SIGALMOX": fmt_num(est_sig),
            "Estoque SAP": fmt_num(est_sap),
            "Divergência": fmt_num(div),
            "Pendente SAP": fmt_num(pend),
            "Status": status,
        })
    return pd.DataFrame(rows)


# ── Conexão Supabase ─────────────────────────────────────────────────────────
url_sb, key_sb = ler_credenciais_supabase()
if not url_sb or not key_sb:
    st.error("Configure SUPABASE_URL e SUPABASE_KEY em `.streamlit/secrets.toml`")
    st.code("""
SUPABASE_URL = "https://azhpxhrwhegfysoeqmft.supabase.co"
SUPABASE_KEY = "sua-anon-key"
APP_PIN = "seu-pin-opcional"
    """)
    st.stop()

sb: Client = criar_sb(url_sb, key_sb)

# Teste de conexão a cada carregamento (limpa erro antigo da sessão)
st.session_state.pop("sb_erro", None)
_con_ok, _con_msg = testar_conexao(url_sb, key_sb)
if _con_ok:
    st.session_state["sb_ok"] = True
else:
    st.session_state["sb_erro"] = _con_msg or "Falha ao conectar no schema almoxarifado."

if st.session_state.get("sb_erro"):
    st.error(st.session_state["sb_erro"])
    with st.expander("Diagnóstico"):
        st.caption(f"URL: {'OK' if url_sb else 'VAZIA'} · Key: {len(key_sb)} caracteres")
        st.caption("Anon key costuma ter ~200 caracteres. Confira Streamlit Cloud → Secrets.")
    st.info("Corrija e clique **Atualizar** (ou Reboot app no Streamlit Cloud).")
elif st.session_state.pop("sb_ok", False):
    pass  # conexão OK — sem banner

# ── Header ───────────────────────────────────────────────────────────────────
c_logo, c_tit, c_btn = st.columns([1.1, 4.9, 1])
with c_logo:
    st.markdown(logo_html(120), unsafe_allow_html=True)
with c_tit:
    st.title("SIGALMOX")
    st.caption("Controle de estoque — retirada física + conciliação SAP · Santa Virgínia")
    st.markdown(f'<p style="margin:0;font-size:13px;">{link_instagram()}</p>', unsafe_allow_html=True)
with c_btn:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.session_state.pop("sb_erro", None)
        st.session_state.pop("sb_ok", None)
        st.rerun()

# Hub cards — setores críticos
st.markdown('<div class="sec">Setores monitorados</div>', unsafe_allow_html=True)
cols = st.columns(6)
hub_items = [
    ("💊", "Medicamentos"), ("🌾", "Nutrição"), ("🛢️", "Lubrificantes"),
    ("⛽", "Combustíveis"), ("🧪", "Defensivos"), ("🔧", "Filtros"),
]
for col, (ico, nome) in zip(cols, hub_items):
    with col:
        st.markdown(
            f'<div class="hub-card active"><div class="ico">{ico}</div>'
            f'<div class="tit">{nome}</div>'
            f'<span class="tag">MONITORADO</span></div>',
            unsafe_allow_html=True,
        )

# ── Abas principais ──────────────────────────────────────────────────────────
tab_estoque, tab_entrada, tab_pend, tab_conc, tab_import, tab_cad = st.tabs([
    "📊 Estoques Críticos",
    "📥 Entrada (NF)",
    "✅ Pendências SAP",
    "🔄 Conciliação",
    "📋 Importar SAP / QR",
    "⚙️ Cadastros",
])

# ══ TAB: Estoques Críticos ═══════════════════════════════════════════════════
with tab_estoque:
    st.markdown('<div class="sec">Consulta de estoque por setor</div>', unsafe_allow_html=True)
    cat_sel = st.selectbox("Setor / categoria", ["Todos"] + CATEGORIAS_CRITICAS, key="cat_estoque")
    if st.button("🔍 Consultar saldo", key="btn_consulta"):
        st.session_state["consulta_feita"] = True

    if st.session_state.get("consulta_feita") or cat_sel != "Todos":
        if cat_sel == "Todos":
            dados = carregar_estoques_criticos(url_sb, key_sb)
        else:
            dados = carregar_produtos(url_sb, key_sb, cat_sel)

        if not dados:
            st.info("Nenhum produto cadastrado neste setor. Importe a lista SAP primeiro.")
        else:
            crit = sum(1 for d in dados if d.get("estoque_minimo") and float(d.get("estoque_atual", 0)) <= float(d["estoque_minimo"]))
            zer = sum(1 for d in dados if float(d.get("estoque_atual", 0)) <= 0)
            m1, m2, m3 = st.columns(3)
            m1.metric("Produtos", len(dados))
            m2.metric("Críticos (≤ mínimo)", crit)
            m3.metric("Zerados", zer)

            df_show = pd.DataFrame([{
                "Código": d.get("codigo_sap", ""),
                "Descrição": d.get("descricao", ""),
                "Categoria": d.get("categoria", ""),
                "Saldo": fmt_num(d.get("estoque_atual", 0)),
                "Mínimo": fmt_num(d.get("estoque_minimo") or "—"),
                "Un": d.get("unidade", "UN"),
                "Status": (
                    "🔴 CRÍTICO" if d.get("estoque_minimo") and float(d.get("estoque_atual", 0)) <= float(d["estoque_minimo"])
                    else "⚠️ ZERADO" if float(d.get("estoque_atual", 0)) <= 0
                    else "✅ OK"
                ),
            } for d in dados])
            dark_table(df_show, height=400)
            st.download_button(
                "⬇️ Exportar Excel",
                gerar_excel(df_show),
                file_name=f"estoque_{cat_sel}_{date.today():%Y%m%d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ══ TAB: Entrada NF ══════════════════════════════════════════════════════════
with tab_entrada:
    st.markdown('<div class="sec">Lançamento de entrada — NF / recebimento</div>', unsafe_allow_html=True)
    produtos = carregar_produtos(url_sb, key_sb)
    if not produtos:
        st.warning("Cadastre produtos via importação SAP antes de lançar entradas.")
    else:
        mapa_prod = {f"{p['codigo_sap']} — {p['descricao']}": p for p in produtos}
        with st.form("form_entrada", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            prod_sel = c1.selectbox("Produto", list(mapa_prod.keys()))
            qtd = c2.number_input("Quantidade", min_value=0.001, value=1.0, step=1.0)
            nf = c3.text_input("Nota Fiscal")
            c4, c5 = st.columns(2)
            fornecedor = c4.text_input("Fornecedor")
            obs = c5.text_input("Observação")
            if st.form_submit_button("📥 Registrar entrada"):
                p = mapa_prod[prod_sel]
                try:
                    tbl(sb, "entradas").insert({
                        "produto_id": p["id"],
                        "quantidade": qtd,
                        "nf": nf or None,
                        "fornecedor": fornecedor or None,
                        "observacao": obs or None,
                    }).execute()
                    st.cache_data.clear()
                    st.success(f"Entrada registrada: {qtd} × {p['descricao']}")
                except Exception as e:
                    st.error(f"Erro ao registrar: {e}")

# ══ TAB: Pendências SAP ══════════════════════════════════════════════════════
with tab_pend:
    st.markdown('<div class="sec">Retiradas físicas aguardando baixa no SAP</div>', unsafe_allow_html=True)
    dia = st.date_input("Filtrar por data", value=date.today())
    pend = carregar_pendencias(url_sb, key_sb)
    mov_dia = carregar_movimentacoes_dia(url_sb, key_sb, str(dia))

    m1, m2, m3 = st.columns(3)
    m1.metric("Pendentes total", len(pend))
    m2.metric(f"Retiradas {dia.strftime('%d/%m')}", len(mov_dia))
    m3.metric("Pendentes do dia", sum(1 for m in mov_dia if not m.get("baixado_sap")))

    if pend:
        df_pend = pd.DataFrame([{
            "Data": fmt_data(m["data_retirada"]),
            "Código": (m.get("produtos") or {}).get("codigo_sap", ""),
            "Produto": (m.get("produtos") or {}).get("descricao", ""),
            "Qtd": fmt_num(m["quantidade"]),
            "Destino": m.get("destino_nome", ""),
            "Retirou": m.get("responsavel_nome", ""),
        } for m in pend])
        dark_table(df_pend, height=300)

        st.markdown('<div class="sec">Marcar baixa no SAP</div>', unsafe_allow_html=True)
        opcoes = {
            f"{fmt_data(m['data_retirada'])} | {(m.get('produtos') or {}).get('codigo_sap','')} | {fmt_num(m['quantidade'])} → {m.get('destino_nome','')}": m
            for m in pend
        }
        sel = st.selectbox("Selecione a retirada", list(opcoes.keys()))
        baixado_por = st.text_input("Baixado por (nome)", value="Almoxarife")
        if st.button("✅ Confirmar baixa no SAP"):
            mov = opcoes[sel]
            try:
                tbl(sb, "movimentacoes").update({
                    "baixado_sap": True,
                    "baixado_sap_em": datetime.now().isoformat(),
                    "baixado_sap_por": baixado_por,
                }).eq("id", mov["id"]).execute()
                st.cache_data.clear()
                st.success("Baixa SAP confirmada!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

        if st.button("✅ Marcar TODAS pendentes do dia como baixadas"):
            ids_dia = [m["id"] for m in mov_dia if not m.get("baixado_sap")]
            if ids_dia:
                for mid in ids_dia:
                    tbl(sb, "movimentacoes").update({
                        "baixado_sap": True,
                        "baixado_sap_em": datetime.now().isoformat(),
                        "baixado_sap_por": baixado_por or "Almoxarife",
                    }).eq("id", mid).execute()
                st.cache_data.clear()
                st.success(f"{len(ids_dia)} retirada(s) marcada(s)!")
                st.rerun()
            else:
                st.info("Nenhuma pendência para este dia.")
    else:
        st.success("Nenhuma retirada pendente de baixa no SAP.")
        df_pend = pd.DataFrame()

    st.download_button(
        "⬇️ Exportar pendências (Excel)",
        gerar_excel(df_pend),
        file_name=f"pendencias_sap_{date.today():%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ══ TAB: Conciliação ═══════════════════════════════════════════════════════════
with tab_conc:
    st.markdown('<div class="sec">Conciliação SIGALMOX × SAP</div>', unsafe_allow_html=True)
    st.caption("Importe o estoque SAP e compare com retiradas físicas registradas no SIGALMOX.")

    cat_conc = st.selectbox("Categoria para conciliar", TODAS_CATEGORIAS, key="cat_conc")
    arquivo_sap = st.file_uploader("Upload estoque SAP (.xlsx)", type=["xlsx", "xls"], key="upload_conc")

    if arquivo_sap and st.button("🔄 Gerar conciliação"):
        try:
            df_sap = ler_excel_sap(arquivo_sap)
            imp = importar_produtos_sap(sb, df_sap, cat_conc, arquivo_sap.name)
            st.session_state["conc_sap_itens"] = df_sap.to_dict("records")
            st.session_state["conc_categoria"] = cat_conc
            st.cache_data.clear()
            st.success(f"Importação OK: {imp['total']} itens ({imp['novos']} novos, {imp['atualizados']} atualizados)")
        except Exception as e:
            st.error(f"Erro na importação: {e}")

    ult_imp = carregar_ultima_importacao(url_sb, key_sb, cat_conc)
    if ult_imp:
        st.caption(f"Última importação SAP ({cat_conc}): {fmt_data(ult_imp['importado_em'])} — {ult_imp['total_itens']} itens")

    produtos_cat = [p for p in carregar_produtos(url_sb, key_sb) if p.get("categoria") == cat_conc]
    if ult_imp:
        sap_itens = carregar_sap_importado(url_sb, key_sb, ult_imp["id"])
    else:
        sap_itens = []
    pend = carregar_pendencias(url_sb, key_sb)
    pend_cat = [m for m in pend if (m.get("produtos") or {}).get("categoria") == cat_conc]

    df_conc = calcular_conciliacao(produtos_cat, sap_itens, pend_cat)
    if not df_conc.empty:
        filtro_status = st.multiselect(
            "Filtrar status",
            ["OK", "BAIXA_PENDENTE_SAP", "DIVERGENCIA_LEVE", "DIVERGENCIA_REAL", "SEM_SAP", "SEM_SIGALMOX"],
            default=["BAIXA_PENDENTE_SAP", "DIVERGENCIA_REAL", "DIVERGENCIA_LEVE"],
        )
        df_filtrado = df_conc[df_conc["Status"].isin(filtro_status)] if filtro_status else df_conc

        ok = len(df_conc[df_conc["Status"] == "OK"])
        pend_sap = len(df_conc[df_conc["Status"] == "BAIXA_PENDENTE_SAP"])
        div_real = len(df_conc[df_conc["Status"] == "DIVERGENCIA_REAL"])
        c1, c2, c3 = st.columns(3)
        c1.metric("✅ OK", ok)
        c2.metric("⏳ Baixa pendente SAP", pend_sap)
        c3.metric("🔴 Divergência real", div_real)

        dark_table(df_filtrado, height=450)
        st.download_button(
            "⬇️ Exportar conciliação",
            gerar_excel(df_filtrado),
            file_name=f"conciliacao_{cat_conc}_{date.today():%Y%m%d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Importe a lista SAP para gerar a conciliação.")

# ══ TAB: Importar SAP / QR ═══════════════════════════════════════════════════
with tab_import:
    st.markdown('<div class="sec">Importar lista SAP → cadastrar produtos + gerar QR</div>', unsafe_allow_html=True)
    cat_imp = st.selectbox("Categoria", TODAS_CATEGORIAS, key="cat_imp")
    arquivo = st.file_uploader("Excel exportado do SAP", type=["xlsx", "xls"], key="upload_imp")

    if arquivo:
        preview = ler_excel_sap(arquivo)
        st.caption(f"Prévia: {len(preview)} produtos detectados")
        dark_table(preview.head(20).rename(columns={
            "codigo": "Código", "descricao": "Descrição", "em_estoque": "Estoque SAP",
        }), height=200)

        if st.button("📥 Importar para SIGALMOX"):
            try:
                result = importar_produtos_sap(sb, preview, cat_imp, arquivo.name)
                st.cache_data.clear()
                st.success(
                    f"Importados {result['total']} itens — "
                    f"{result['novos']} novos, {result['atualizados']} existentes"
                )
                st.session_state["ult_import_cat"] = cat_imp
                st.session_state["ult_import_df"] = preview
            except Exception as e:
                st.error(f"Erro: {e}")

    st.markdown('<div class="sec">Gerar PDF de etiquetas QR</div>', unsafe_allow_html=True)
    st.caption("Formato QR: `SIGALMOX-{codigo_sap}` — cole nas prateleiras e pastas.")
    if st.session_state.get("ult_import_df") is not None:
        if st.button("🏷️ Gerar PDF de etiquetas"):
            try:
                from gerar_qr_etiquetas import gerar_pdf_bytes
                pdf_bytes = gerar_pdf_bytes(
                    st.session_state["ult_import_df"],
                    st.session_state.get("ult_import_cat", cat_imp),
                )
                st.download_button(
                    "⬇️ Baixar PDF de etiquetas",
                    pdf_bytes,
                    file_name=f"etiquetas_{cat_imp}_{date.today():%Y%m%d}.pdf",
                    mime="application/pdf",
                )
            except ImportError:
                st.warning("Instale dependências: pip install qrcode reportlab")
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")
    else:
        st.info("Importe uma lista SAP primeiro para gerar as etiquetas.")

# ══ TAB: Cadastros ═══════════════════════════════════════════════════════════
with tab_cad:
    st.markdown('<div class="sec">Cadastros auxiliares</div>', unsafe_allow_html=True)
    sub_dest, sub_resp, sub_min = st.tabs(["Destinos", "Responsáveis", "Estoque mínimo"])

    with sub_dest:
        with st.form("form_destino"):
            nome_dest = st.text_input("Nome do destino")
            setor_dest = st.text_input("Setor")
            if st.form_submit_button("Adicionar destino"):
                try:
                    tbl(sb, "destinos").insert({"nome": nome_dest, "setor": setor_dest}).execute()
                    st.cache_data.clear()
                    st.success(f"Destino '{nome_dest}' cadastrado.")
                except Exception as e:
                    st.error(str(e))
        destinos = carregar_destinos(url_sb, key_sb)
        dark_table(pd.DataFrame([{"Nome": d["nome"], "Setor": d.get("setor", "")} for d in destinos]))

    with sub_resp:
        with st.form("form_resp"):
            nome_resp = st.text_input("Nome do responsável")
            if st.form_submit_button("Adicionar responsável"):
                try:
                    tbl(sb, "responsaveis").insert({"nome": nome_resp}).execute()
                    st.cache_data.clear()
                    st.success(f"Responsável '{nome_resp}' cadastrado.")
                except Exception as e:
                    st.error(str(e))
        responsaveis = carregar_responsaveis(url_sb, key_sb)
        dark_table(pd.DataFrame([{"Nome": r["nome"]} for r in responsaveis]))

    with sub_min:
        st.caption("Defina estoque mínimo para alertas nos setores críticos.")
        prods = [p for p in carregar_produtos(url_sb, key_sb) if p.get("categoria") in CATEGORIAS_CRITICAS]
        if prods:
            mapa = {f"{p['codigo_sap']} — {p['descricao']}": p for p in prods}
            sel_p = st.selectbox("Produto", list(mapa.keys()), key="sel_min")
            minimo = st.number_input("Estoque mínimo", min_value=0.0, value=0.0, step=1.0)
            if st.button("💾 Salvar mínimo"):
                p = mapa[sel_p]
                tbl(sb, "produtos").update({"estoque_minimo": minimo}).eq("id", p["id"]).execute()
                st.cache_data.clear()
                st.success("Estoque mínimo atualizado.")

st.markdown("---")
st.caption("SIGALMOX · Santa Virgínia · PWA de retirada: pwa-sigalmox/index.html")
