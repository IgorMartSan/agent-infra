# SQLAgent — Agente de Consulta Somente Leitura em Banco SQL

Documentação personalizada do serviço `py-sql-agent-job`.

## Visão Geral

O SQLAgent é um worker que responde perguntas em linguagem natural sobre um banco PostgreSQL, executando **apenas consultas de leitura**. Você configura login e senha em variáveis de ambiente, e o agente usa essas credenciais para explorar o schema e responder perguntas — nunca para modificar dados.

O agente é movido pelo modelo Google Gemma 4 E4B (via API compatível com OpenAI) e orquestrado com LangChain/LangGraph.

## O que o agente faz (verificado no código)

1. Consome mensagens da fila RabbitMQ `agent.sql.requests` (routing key `agent.sql`).
2. Valida o payload: o campo `message` deve ser uma string não vazia.
3. Executa a mensagem num agente LangGraph com três ferramentas SQL.
4. Publica a resposta em `chat:response:{application_id}:{conversation_id}` no Redis Pub/Sub, que o frontend recebe via SSE.

## Autenticação no banco

As credenciais ficam no arquivo `.env` (nunca na conversa com o agente):

```env
SQL_DATABASE_HOST=host-do-banco
SQL_DATABASE_PORT=5432
SQL_DATABASE_NAME=nome_do_banco
SQL_DATABASE_USER=usuario_somente_leitura
SQL_DATABASE_PASSWORD=troque-esta-senha
SQL_DATABASE_SCHEMA=public
```

O agente não aceita login/senha via mensagem: o prompt de sistema proíbe revelar credenciais ou detalhes de conexão, e a URL de conexão é montada internamente pelo SQLAlchemy sem expor usuário/senha em logs.

Recomendação: crie um usuário dedicado no PostgreSQL com permissão apenas de `SELECT`, mesmo que o agente já bloqueie escritas por outras camadas.

## Três camadas de proteção somente leitura

| Camada | Onde | Como funciona |
| --- | --- | --- |
| 1. Prompt | `src/prompts/system_prompt.py` | Instrui o modelo a executar apenas leitura e nunca usar INSERT/UPDATE/DELETE/CREATE/DROP etc. |
| 2. Validação sintática | `src/tools/sql_database.py` → `_validate_read_only_query` | `sqlparse` recusa qualquer instrução que não seja SELECT, WITH...SELECT, EXPLAIN ou SHOW; só uma instrução por consulta. |
| 3. Banco de dados | `src/infra/sql_database/connection.py` | A conexão é aberta com `default_transaction_read_only=on`, e cada consulta roda em transação `READ ONLY` com `statement_timeout`. |

Ou seja: mesmo que o modelo tente algo fora do permitido, a camada 2 recusa o texto e a camada 3 garantiria o bloqueio no próprio PostgreSQL.

## Ferramentas disponíveis ao agente

| Ferramenta | Descrição |
| --- | --- |
| `list_database_objects` | Lista tabelas e views do schema configurado. |
| `describe_database_tables` | Retorna colunas, chaves primárias e estrangeiras das tabelas informadas. |
| `execute_read_only_sql` | Executa a consulta validada e retorna no máximo `SQL_MAX_ROWS` linhas (padrão 100), com indicação de truncamento. |

## Variáveis de ambiente completas

### Infraestrutura de mensageria

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `AGENT_ID` | `sql-agent` | Identificador do agente no gateway |
| `RABBITMQ_HOST` | `rabbitmq` | Host do RabbitMQ |
| `RABBITMQ_PORT` | `5672` | Porta do RabbitMQ |
| `RABBITMQ_USER` / `RABBITMQ_PASSWORD` | `admin` / `admin123` | Credenciais do RabbitMQ |
| `RABBITMQ_EXCHANGE` | `agent.requests` | Exchange de entrada |
| `RABBITMQ_QUEUE` | `agent.sql.requests` | Fila do agente |
| `RABBITMQ_ROUTING_KEY` | `agent.sql` | Chave de roteamento |
| `RABBITMQ_PREFETCH_COUNT` | `1` | Mensagens simultâneas por worker |

### Redis

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `REDIS_HOST` / `REDIS_PORT` | `redis` / `6379` | Conexão Redis |
| `REDIS_RESPONSE_CHANNEL_PREFIX` | `chat:response` | Prefixo do canal Pub/Sub de respostas |

### Modelo (API compatível com OpenAI)

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `OPENAI_BASE_URL` | `http://10.247.168.43:8072/v1` | Servidor vLLM local |
| `OPENAI_MODEL` | `gemma4` | Modelo exposto pela API |
| `OPENAI_TEMPERATURE` | `0.2` | Baixa temperatura para respostas determinísticas |
| `OPENAI_MAX_TOKENS` | `1024` | Limite de saída |
| `OPENAI_TIMEOUT_SECONDS` | `120` | Timeout de inferência |

### Banco SQL

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `SQL_DATABASE_DRIVER` | `postgresql+psycopg` | Driver SQLAlchemy |
| `SQL_QUERY_TIMEOUT_SECONDS` | `30` | Timeout de cada consulta |
| `SQL_MAX_ROWS` | `100` | Máximo de linhas retornadas |
| `SQL_AGENT_RECURSION_LIMIT` | `12` | Limite de iterações do agente |

## Arquitetura do fluxo

```
Usuário/API
   │  POST /api/v1/messages
   ▼
Gateway ──► RabbitMQ (agent.requests / agent.sql.requests)
                 │
                 ▼
        Worker main.py (loop com reconexão)
                 │  process_agent_message (valida payload)
                 ▼
        LangGraph: receive_message
                 │  agente LangChain + prompt de sistema + 3 ferramentas SQL
                 ▼
        PostgreSQL (READ ONLY, statement_timeout)
                 │
                 ▼
        Redis Pub/Sub: chat:response:{application_id}:{conversation_id}
                 │
                 ▼
        Frontend (SSE) / chat.py (CLI de teste)
```

## Como executar

### Via Docker

O serviço faz parte do `docker-compose` do repositório; a imagem é construída pelo `Dockerfile` do serviço.

### Local (desenvolvimento)

```powershell
cd services\jobs\py-sql-agent-job
copy .env.example .env   # ajuste credenciais do banco
uv sync
uv run python -m src.main
```

### Testar em conversa (CLI)

Com a API do gateway e o Redis acessíveis:

```powershell
uv run python chat.py
```

Digite perguntas como "quais tabelas existem no banco?" ou "quantos registros há na tabela X?".

### Testes automatizados

```powershell
uv run pytest
uv run ruff check .
```

## Formato do payload de entrada

```json
{
  "application_id": "sql-chat-cli",
  "user_id": "chat-cli-user",
  "chat_id": "sql-chat-1",
  "agent_id": "sql-agent",
  "message": "Quantos clientes estão ativos?"
}
```

Payloads sem `message` válida são descartados sem reprocessamento (`InvalidMessageError`); outros erros devolvem a mensagem à fila.

## Evento de resposta

```json
{
  "type": "message.completed",
  "application_id": "...",
  "conversation_id": "...",
  "message_id": "...",
  "agent_id": "sql-agent",
  "content": "Resposta textual do agente"
}
```

## Observações e limitações

- **Persistência PostgreSQL da resposta ainda não implementada**: há um comentário no `src/main.py` marcando onde será adicionada.
- O modelo tem contexto total de 4.096 tokens; consultas muito grandes podem degradar a resposta (mitigado pelo `SQL_MAX_ROWS`).
- `RABBITMQ_PREFETCH_COUNT=1` limita o worker a uma mensagem por vez, adequado à capacidade atual do servidor de modelo.
- Pool de conexões SQL com `pool_size=1` e `max_overflow=0`: uma conexão por instância, com `pool_pre_ping`.