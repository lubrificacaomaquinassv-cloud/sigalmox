-- Adiciona destino SESTR (rodar no SQL Editor se schema já aplicado)
INSERT INTO almoxarifado.destinos (nome, setor) VALUES
  ('SESTR', 'SESTR')
ON CONFLICT (nome) DO NOTHING;
