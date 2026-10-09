# infra

## Arquitetura de Pacotes Compartilhados

A arquitetura e estrutura de adaptadores reutilizáveis estão documentadas em:

- 📄 [ARCHITECTURE.md](ARCHITECTURE.md)


Pacote de adaptadores reutilizáveis em `src/infra/`. Contém conexão e repositório Redis para agrupamento de mensagens, repositório PostgreSQL para lotes e utilitários MongoDB. O fluxo padrão do gateway, chat e workers mantém seus próprios adaptadores nos respectivos serviços; os recursos deste pacote só atuam onde são importados explicitamente.

A suite `tests/redis/test_message_group_repository_integration.py` é de integração e requer um Redis de teste separado do banco de produção. Configure `RUN_REDIS_INTEGRATION=1` e `TEST_REDIS_HOST/PORT/DB/PASSWORD`; o teste rejeita DB 0 e limpa o banco de teste antes e depois. `packages/infra/pyproject.toml` lista Redis, SQLAlchemy, psycopg2 e PyMongo como dependências.

~~~powershell
cd packages/infra
uv run python -m unittest discover -s tests/redis -p "*_integration.py" -v
~~~

Use um `TEST_REDIS_DB` exclusivo ao ativar o teste de integração.
