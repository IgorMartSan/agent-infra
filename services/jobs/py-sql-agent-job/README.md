# SQL Agent Job

Worker SQL independente que serviu de base ao `argus-agent`. Ele usa `SQLDatabaseToolkit` para descobrir tabelas, ler a estrutura e responder perguntas sobre um PostgreSQL. No Compose atual o agente ativo é o [Argus no worker unificado](../py-agent-job/README.md); este job permanece disponível para execução separada.

`src/graph/` contém o grafo e a memória em processo; `src/infra/sql_database/` monta a conexão; `src/processor.py` valida a mensagem; `src/main.py` consome `agent.sql.requests` e publica no Redis. A conexão PostgreSQL usa `default_transaction_read_only=on` e timeout de instrução. Use também uma conta com permissões somente de leitura no banco.

Configure `.env` com `SQL_DATABASE_HOST/PORT/NAME/USER/PASSWORD`, `SQL_DATABASE_SCHEMA`, `OPENAI_BASE_URL/MODEL/API_KEY`, Redis e RabbitMQ. `AGENT_ID=sql-agent` usa a rota `agent.sql`. O Argus utiliza o mesmo `.env` local no Compose, mas a própria fila e ID.

~~~powershell
cd services/jobs/py-sql-agent-job
uv sync --frozen
uv run pytest tests
~~~

[Documentação adicional](DOCUMENTACAO.md) descreve o formato do payload e os limites da conexão.
