-- SIGALMOX — Força PostgREST a reconhecer schema almoxarifado
-- Rode no SQL Editor se o app mostrar "schema inacessível" mesmo após Save no dashboard

ALTER ROLE authenticator RESET pgrst.db_schemas;
NOTIFY pgrst, 'reload schema';

-- Confirme permissões (seguro rodar de novo)
GRANT USAGE ON SCHEMA almoxarifado TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA almoxarifado TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA almoxarifado TO anon, authenticated, service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA almoxarifado TO anon, authenticated, service_role;
