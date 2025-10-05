Database reset

```bash
docker compose exec -T db-bible pg_dump -U profeta -d biblia > backup_pre_ara_import_$(date +%Y%m%d_%H%M%S).sql

docker compose exec db-bible psql -U profeta -d postgres -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'biblia' AND pid <> pg_backend_pid();"

docker compose exec db-bible psql -U profeta -c "DROP DATABASE IF EXISTS biblia;"
docker compose exec db-bible psql -U profeta -c "CREATE DATABASE biblia;"

docker compose exec -T db-bible psql -U profeta -d biblia < backup_pre_ara_import_20251005_223639.sql
```

```sql
SELECT setval('versao_id_seq', (SELECT COALESCE(MAX(id), 1) FROM versao));

-- Atualizar sequência da tabela versiculo
SELECT setval('versiculo_id_seq', (SELECT COALESCE(MAX(id), 1) FROM versiculo));

-- Atualizar sequência da tabela livro
SELECT setval('livro_id_seq', (SELECT COALESCE(MAX(id), 1) FROM livro));

-- Atualizar sequência da tabela testamento
SELECT setval('testamento_id_seq', (SELECT COALESCE(MAX(id), 1) FROM testamento));

-- Atualizar sequência da tabela livrocapitulonumeroversiculos
SELECT setval('livrocapitulonumeroversiculos_id_seq', (SELECT COALESCE(MAX(id), 1) FROM
livrocapitulonumeroversiculos));

-- Verificar sequências atualizadas
SELECT
    schemaname,
    sequencename,
    last_value
FROM pg_sequences
WHERE schemaname = 'public'
ORDER BY sequencename;
```