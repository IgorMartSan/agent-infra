## Testes de integração do Redis

Os testes usam o banco Redis 15 e executam `FLUSHDB` antes e depois de cada caso.
Inicie o Redis e execute a suíte a partir de `packages/infra`:

```bash
docker compose -f ../../composes/compose.redis.yaml up -d redis
RUN_REDIS_INTEGRATION=1 PYTHONPATH=src uv run --frozen python -m unittest discover \
  -s tests/redis -p '*_integration.py' -v
```

Use `TEST_REDIS_HOST`, `TEST_REDIS_PORT`, `TEST_REDIS_DB` e
`TEST_REDIS_PASSWORD` para apontar os testes para outra instância. Por segurança,
o banco 0 não é aceito.
