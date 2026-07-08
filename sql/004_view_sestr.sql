-- Inclui SESTR na view de estoques críticos (rodar se schema já aplicado)
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
    'Combustíveis', 'Defensivos Agrícola', 'Filtros', 'SESTR'
  );
