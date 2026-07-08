-- SIGALMOX — Schema almoxarifado (Supabase / Postgres)
-- Projeto: azhpxhrwhegfysoeqmft
-- Rodar no SQL Editor do Supabase
-- Depois: Settings > API > Exposed schemas → adicionar "almoxarifado"

CREATE SCHEMA IF NOT EXISTS almoxarifado;

-- ── Produtos (cadastro central) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS almoxarifado.produtos (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo_sap      TEXT NOT NULL,
  qr_code         TEXT NOT NULL,
  descricao       TEXT NOT NULL,
  categoria       TEXT NOT NULL,
  local_tipo      TEXT NOT NULL DEFAULT 'interno'
                  CHECK (local_tipo IN ('interno', 'externo')),
  estoque_atual   NUMERIC(14, 3) NOT NULL DEFAULT 0,
  estoque_minimo  NUMERIC(14, 3),
  unidade         TEXT NOT NULL DEFAULT 'UN',
  ativo           BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (codigo_sap),
  UNIQUE (qr_code)
);

CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON almoxarifado.produtos (categoria);
CREATE INDEX IF NOT EXISTS idx_produtos_codigo ON almoxarifado.produtos (codigo_sap);
CREATE INDEX IF NOT EXISTS idx_produtos_ativo ON almoxarifado.produtos (ativo) WHERE ativo = TRUE;

-- ── Destinos (setores / locais de retirada) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS almoxarifado.destinos (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome        TEXT NOT NULL UNIQUE,
  setor       TEXT,
  ativo       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Responsáveis (quem retira fisicamente) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS almoxarifado.responsaveis (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome        TEXT NOT NULL UNIQUE,
  ativo       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Movimentações — SAÍDA via scan QR ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS almoxarifado.movimentacoes (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  produto_id        UUID NOT NULL REFERENCES almoxarifado.produtos(id),
  quantidade        NUMERIC(14, 3) NOT NULL CHECK (quantidade > 0),
  destino_id        UUID REFERENCES almoxarifado.destinos(id),
  destino_nome      TEXT NOT NULL,
  responsavel_id    UUID REFERENCES almoxarifado.responsaveis(id),
  responsavel_nome  TEXT NOT NULL,
  data_retirada     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  baixado_sap       BOOLEAN NOT NULL DEFAULT FALSE,
  baixado_sap_em    TIMESTAMPTZ,
  baixado_sap_por   TEXT,
  observacao        TEXT,
  origem            TEXT NOT NULL DEFAULT 'pwa' CHECK (origem IN ('pwa', 'streamlit', 'manual')),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mov_produto ON almoxarifado.movimentacoes (produto_id);
CREATE INDEX IF NOT EXISTS idx_mov_data ON almoxarifado.movimentacoes (data_retirada DESC);
CREATE INDEX IF NOT EXISTS idx_mov_baixado ON almoxarifado.movimentacoes (baixado_sap) WHERE baixado_sap = FALSE;

-- ── Entradas — NF / lançamento manual ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS almoxarifado.entradas (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  produto_id      UUID NOT NULL REFERENCES almoxarifado.produtos(id),
  quantidade      NUMERIC(14, 3) NOT NULL CHECK (quantidade > 0),
  nf              TEXT,
  fornecedor      TEXT,
  data_entrada    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  lancado_sap     BOOLEAN NOT NULL DEFAULT FALSE,
  lancado_sap_em  TIMESTAMPTZ,
  observacao      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entrada_produto ON almoxarifado.entradas (produto_id);
CREATE INDEX IF NOT EXISTS idx_entrada_data ON almoxarifado.entradas (data_entrada DESC);

-- ── Importação SAP (snapshot a cada upload) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS almoxarifado.sap_importacao (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  arquivo_nome  TEXT,
  categoria     TEXT,
  total_itens   INT NOT NULL DEFAULT 0,
  importado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS almoxarifado.sap_estoque_importado (
  id              BIGSERIAL PRIMARY KEY,
  importacao_id   UUID NOT NULL REFERENCES almoxarifado.sap_importacao(id) ON DELETE CASCADE,
  codigo_sap      TEXT NOT NULL,
  descricao       TEXT NOT NULL,
  qtd_sap         NUMERIC(14, 3) NOT NULL DEFAULT 0,
  categoria       TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sap_imp_importacao ON almoxarifado.sap_estoque_importado (importacao_id);
CREATE INDEX IF NOT EXISTS idx_sap_imp_codigo ON almoxarifado.sap_estoque_importado (codigo_sap);

-- ── Triggers: baixa / entrada automática de estoque ─────────────────────────
CREATE OR REPLACE FUNCTION almoxarifado.fn_baixa_estoque()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE almoxarifado.produtos
  SET estoque_atual = GREATEST(0, estoque_atual - NEW.quantidade),
      updated_at = NOW()
  WHERE id = NEW.produto_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_baixa_estoque ON almoxarifado.movimentacoes;
CREATE TRIGGER trg_baixa_estoque
  AFTER INSERT ON almoxarifado.movimentacoes
  FOR EACH ROW EXECUTE FUNCTION almoxarifado.fn_baixa_estoque();

CREATE OR REPLACE FUNCTION almoxarifado.fn_entrada_estoque()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE almoxarifado.produtos
  SET estoque_atual = estoque_atual + NEW.quantidade,
      updated_at = NOW()
  WHERE id = NEW.produto_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_entrada_estoque ON almoxarifado.entradas;
CREATE TRIGGER trg_entrada_estoque
  AFTER INSERT ON almoxarifado.entradas
  FOR EACH ROW EXECUTE FUNCTION almoxarifado.fn_entrada_estoque();

-- ── View: conciliação SIGALMOX × SAP ─────────────────────────────────────────
CREATE OR REPLACE VIEW almoxarifado.v_conciliacao AS
WITH ultima_importacao AS (
  SELECT DISTINCT ON (categoria)
    id, categoria, importado_em
  FROM almoxarifado.sap_importacao
  ORDER BY categoria, importado_em DESC
),
sap_atual AS (
  SELECT
    si.codigo_sap,
    si.descricao,
    si.qtd_sap,
    si.categoria,
    ui.importado_em AS sap_importado_em
  FROM almoxarifado.sap_estoque_importado si
  JOIN ultima_importacao ui ON ui.id = si.importacao_id
),
retiradas_pendentes AS (
  SELECT
    p.codigo_sap,
    SUM(m.quantidade) AS qtd_retirada_sigalmox,
    COUNT(*) AS num_retiradas,
    MIN(m.data_retirada) AS primeira_retirada,
    MAX(m.data_retirada) AS ultima_retirada
  FROM almoxarifado.movimentacoes m
  JOIN almoxarifado.produtos p ON p.id = m.produto_id
  WHERE m.baixado_sap = FALSE
  GROUP BY p.codigo_sap
),
retiradas_todas AS (
  SELECT
    p.codigo_sap,
    SUM(m.quantidade) AS qtd_retirada_total
  FROM almoxarifado.movimentacoes m
  JOIN almoxarifado.produtos p ON p.id = m.produto_id
  GROUP BY p.codigo_sap
)
SELECT
  COALESCE(s.codigo_sap, p.codigo_sap) AS codigo_sap,
  COALESCE(s.descricao, p.descricao) AS descricao,
  COALESCE(s.categoria, p.categoria) AS categoria,
  COALESCE(p.estoque_atual, 0) AS estoque_sigalmox,
  COALESCE(s.qtd_sap, 0) AS estoque_sap,
  COALESCE(p.estoque_atual, 0) - COALESCE(s.qtd_sap, 0) AS divergencia_estoque,
  COALESCE(rp.qtd_retirada_sigalmox, 0) AS qtd_pendente_sap,
  COALESCE(rp.num_retiradas, 0) AS retiradas_pendentes,
  CASE
    WHEN s.codigo_sap IS NULL THEN 'SEM_SAP'
    WHEN p.codigo_sap IS NULL THEN 'SEM_SIGALMOX'
    WHEN COALESCE(rp.qtd_retirada_sigalmox, 0) > 0 THEN 'BAIXA_PENDENTE_SAP'
    WHEN ABS(COALESCE(p.estoque_atual, 0) - COALESCE(s.qtd_sap, 0)) <= 0.001 THEN 'OK'
    WHEN ABS(COALESCE(p.estoque_atual, 0) - COALESCE(s.qtd_sap, 0)) <= 1 THEN 'DIVERGENCIA_LEVE'
    ELSE 'DIVERGENCIA_REAL'
  END AS status_conciliacao,
  s.sap_importado_em,
  rp.primeira_retirada,
  rp.ultima_retirada
FROM almoxarifado.produtos p
FULL OUTER JOIN sap_atual s ON s.codigo_sap = p.codigo_sap
LEFT JOIN retiradas_pendentes rp ON rp.codigo_sap = COALESCE(s.codigo_sap, p.codigo_sap)
WHERE p.ativo = TRUE OR p.id IS NULL;

-- ── View: estoques críticos ─────────────────────────────────────────────────
CREATE OR REPLACE VIEW almoxarifado.v_estoques_criticos AS
SELECT
  p.id,
  p.codigo_sap,
  p.descricao,
  p.categoria,
  p.estoque_atual,
  p.estoque_minimo,
  p.unidade,
  p.local_tipo,
  CASE
    WHEN p.estoque_minimo IS NOT NULL AND p.estoque_atual <= p.estoque_minimo THEN 'CRITICO'
    WHEN p.estoque_minimo IS NOT NULL AND p.estoque_atual <= p.estoque_minimo * 1.5 THEN 'ATENCAO'
    WHEN p.estoque_atual <= 0 THEN 'ZERADO'
    ELSE 'OK'
  END AS status_estoque,
  CASE
    WHEN p.estoque_minimo IS NOT NULL AND p.estoque_minimo > 0
    THEN ROUND((p.estoque_atual / p.estoque_minimo) * 100, 1)
    ELSE NULL
  END AS pct_minimo
FROM almoxarifado.produtos p
WHERE p.ativo = TRUE
  AND p.categoria IN (
    'Medicamentos Pecuária', 'Nutrição Animal', 'Lubrificantes',
    'Combustíveis', 'Defensivos Agrícola', 'Filtros'
  );

-- ── View: pendências SAP (retiradas do dia) ─────────────────────────────────
CREATE OR REPLACE VIEW almoxarifado.v_pendencias_sap AS
SELECT
  m.id,
  m.data_retirada,
  p.codigo_sap,
  p.descricao,
  p.categoria,
  m.quantidade,
  m.destino_nome,
  m.responsavel_nome,
  m.observacao,
  m.baixado_sap,
  m.baixado_sap_em
FROM almoxarifado.movimentacoes m
JOIN almoxarifado.produtos p ON p.id = m.produto_id
WHERE m.baixado_sap = FALSE
ORDER BY m.data_retirada DESC;

-- ── Dados iniciais: categorias, destinos, responsáveis ───────────────────────
INSERT INTO almoxarifado.destinos (nome, setor) VALUES
  ('Pecuária — Curral', 'Pecuária'),
  ('Pecuária — Tratamento', 'Pecuária'),
  ('Máquinas — Campo', 'Máquinas'),
  ('Máquinas — Oficina', 'Máquinas'),
  ('Florestal — Viveiro', 'Florestal'),
  ('Florestal — Plantio', 'Florestal'),
  ('Borracharia', 'Oficina'),
  ('Manutenção Geral', 'Oficina'),
  ('Agricultura — Pulverização', 'Agricultura'),
  ('Agricultura — Plantio', 'Agricultura'),
  ('Refeitório', 'Administração'),
  ('Administração', 'Administração')
ON CONFLICT (nome) DO NOTHING;

INSERT INTO almoxarifado.responsaveis (nome) VALUES
  ('Almoxarife'),
  ('Encarregado Pecuária'),
  ('Encarregado Máquinas'),
  ('Encarregado Florestal'),
  ('Borracheiro'),
  ('Mecânico'),
  ('Operador Agrícola')
ON CONFLICT (nome) DO NOTHING;

-- ── RLS ─────────────────────────────────────────────────────────────────────
ALTER TABLE almoxarifado.produtos ENABLE ROW LEVEL SECURITY;
ALTER TABLE almoxarifado.destinos ENABLE ROW LEVEL SECURITY;
ALTER TABLE almoxarifado.responsaveis ENABLE ROW LEVEL SECURITY;
ALTER TABLE almoxarifado.movimentacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE almoxarifado.entradas ENABLE ROW LEVEL SECURITY;
ALTER TABLE almoxarifado.sap_importacao ENABLE ROW LEVEL SECURITY;
ALTER TABLE almoxarifado.sap_estoque_importado ENABLE ROW LEVEL SECURITY;

-- Políticas permissivas (anon + authenticated) — ajuste conforme necessidade
DO $$ DECLARE t TEXT; BEGIN
  FOREACH t IN ARRAY ARRAY[
    'produtos','destinos','responsaveis','movimentacoes',
    'entradas','sap_importacao','sap_estoque_importado'
  ] LOOP
    EXECUTE format('DROP POLICY IF EXISTS almox_%s_all ON almoxarifado.%s', t, t);
    EXECUTE format(
      'CREATE POLICY almox_%s_all ON almoxarifado.%s FOR ALL TO anon, authenticated USING (true) WITH CHECK (true)',
      t, t
    );
  END LOOP;
END $$;

-- Grants para PostgREST
GRANT USAGE ON SCHEMA almoxarifado TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA almoxarifado TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA almoxarifado TO anon, authenticated, service_role;
GRANT SELECT ON almoxarifado.v_conciliacao TO anon, authenticated, service_role;
GRANT SELECT ON almoxarifado.v_estoques_criticos TO anon, authenticated, service_role;
GRANT SELECT ON almoxarifado.v_pendencias_sap TO anon, authenticated, service_role;
