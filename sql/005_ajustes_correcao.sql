-- SIGALMOX — Correções / estorno de saída lançada a mais
-- Rodar no SQL Editor do Supabase (schema almoxarifado já exposto)

CREATE TABLE IF NOT EXISTS almoxarifado.ajustes (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  produto_id            UUID NOT NULL REFERENCES almoxarifado.produtos(id),
  movimentacao_id       UUID REFERENCES almoxarifado.movimentacoes(id),
  tipo                  TEXT NOT NULL CHECK (tipo IN ('estorno_excesso', 'correcao_saida_extra')),
  quantidade            NUMERIC(14, 3) NOT NULL CHECK (quantidade > 0),
  quantidade_registrada NUMERIC(14, 3),
  quantidade_correta    NUMERIC(14, 3),
  motivo                TEXT NOT NULL,
  responsavel_nome      TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ajustes_mov ON almoxarifado.ajustes (movimentacao_id);
CREATE INDEX IF NOT EXISTS idx_ajustes_produto ON almoxarifado.ajustes (produto_id);

CREATE OR REPLACE FUNCTION almoxarifado.fn_ajuste_estoque()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.tipo = 'estorno_excesso' THEN
    UPDATE almoxarifado.produtos
    SET estoque_atual = estoque_atual + NEW.quantidade,
        updated_at = NOW()
    WHERE id = NEW.produto_id;
  ELSIF NEW.tipo = 'correcao_saida_extra' THEN
    UPDATE almoxarifado.produtos
    SET estoque_atual = GREATEST(0, estoque_atual - NEW.quantidade),
        updated_at = NOW()
    WHERE id = NEW.produto_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ajuste_estoque ON almoxarifado.ajustes;
CREATE TRIGGER trg_ajuste_estoque
  AFTER INSERT ON almoxarifado.ajustes
  FOR EACH ROW EXECUTE FUNCTION almoxarifado.fn_ajuste_estoque();

ALTER TABLE almoxarifado.ajustes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS almox_ajustes_all ON almoxarifado.ajustes;
CREATE POLICY almox_ajustes_all ON almoxarifado.ajustes
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

GRANT ALL ON almoxarifado.ajustes TO anon, authenticated, service_role;

-- View: quantidade efetiva de saída (original − estornos + correções extras)
CREATE OR REPLACE VIEW almoxarifado.v_movimentacoes_efetivas AS
SELECT
  m.id,
  m.produto_id,
  m.quantidade AS quantidade_registrada,
  COALESCE(SUM(CASE WHEN a.tipo = 'estorno_excesso' THEN a.quantidade ELSE 0 END), 0) AS total_estornado,
  COALESCE(SUM(CASE WHEN a.tipo = 'correcao_saida_extra' THEN a.quantidade ELSE 0 END), 0) AS total_extra,
  m.quantidade
    - COALESCE(SUM(CASE WHEN a.tipo = 'estorno_excesso' THEN a.quantidade ELSE 0 END), 0)
    + COALESCE(SUM(CASE WHEN a.tipo = 'correcao_saida_extra' THEN a.quantidade ELSE 0 END), 0)
    AS quantidade_efetiva,
  m.data_retirada,
  m.destino_nome,
  m.responsavel_nome,
  m.baixado_sap,
  m.observacao
FROM almoxarifado.movimentacoes m
LEFT JOIN almoxarifado.ajustes a ON a.movimentacao_id = m.id
GROUP BY m.id;

GRANT SELECT ON almoxarifado.v_movimentacoes_efetivas TO anon, authenticated, service_role;
