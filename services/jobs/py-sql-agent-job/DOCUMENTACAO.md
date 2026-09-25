# Detalhes do SQL Agent

Consulte o [README do serviço](README.md) para iniciar e testar o worker. Este arquivo registra o contrato que o `argus-agent` também aproveita.

A fila independente do SQL Agent é `agent.sql.requests` com chave `agent.sql`. O gateway recebe `application_id`, `chat_id`, `agent_id=sql-agent` e `message`; o worker publica `message.completed` ou `message.failed` no canal Redis `chat:response:{application_id}:{chat_id}`. No Compose padrão, o Argus usa `agent_id=argus-agent`, a chave `agent.argus` e `agent.argus.requests`.

O agente ativo usa `SQLDatabaseToolkit`: descobre tabelas, consulta metadados e executa SQL. O arquivo `src/tools/sql_database.py` contém ferramentas adicionais com validação sintática, mas o grafo atual em `src/graph/nodes.py` chama o toolkit do LangChain. A proteção efetiva do banco é a conexão com `default_transaction_read_only=on`, o `statement_timeout` e as permissões do usuário PostgreSQL. O prompt também pede somente leitura; configure uma conta com `SELECT`.

`SQL_DATABASE_HOST/PORT/NAME/USER/PASSWORD` formam a URL de conexão; `SQL_DATABASE_SCHEMA` informa o schema desejado no prompt e nas ferramentas adicionais. `SQL_QUERY_TIMEOUT_SECONDS` controla o timeout, `SQL_AGENT_RECURSION_LIMIT` o número de passos e `OPENAI_BASE_URL/MODEL/API_KEY` apontam ao modelo. A memória é guardada no processo com limite de 60 mensagens de conversa por thread.
