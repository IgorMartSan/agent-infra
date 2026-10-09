# Agent Gateway API

Gateway FastAPI que recebe texto em `POST /api/v1/messages` e publica no exchange RabbitMQ `agent.requests`. `GET /api/v1/agents` lista agentes com heartbeat ativo no Redis; `GET /` responde a uma checagem simples sem depender do broker.

## Mensagens

~~~json
{
  "application_id": "erp",
  "user_id": "usuario-1",
  "chat_id": "conversa-1",
  "agent_id": "argus-agent",
  "message": "Quais tabelas existem?",
  "delivery": {"type": "NONE"}
}
~~~

O gateway responde `202` com `message_id` e `status: ACCEPTED` após a confirmação do RabbitMQ. Retorna `409` se a conversa já tem uma mensagem em processamento, `503` se o agente não está ativo, a fila está cheia ou a infraestrutura está indisponível, e `422` para payload inválido. `delivery` aceita `NONE`, `HTTP`, `WEBSOCKET` e `GOOGLE_CHAT` no contrato, mas o caminho ativo entrega as respostas pelo Redis/SSE.

O roteamento segue `agent_id`: `argus-agent` usa `agent.argus` e a fila `agent.argus.requests`. O worker cria o binding da sua fila. O gateway verifica a profundidade da fila e segura um lock Redis por aplicação, chat e agente até o worker publicar a resposta.

## Arquitetura do Serviço

A arquitetura detalhada de pastas, contratos e responsabilidades das camadas (`routers`, `schemas`, `service`, `infra`, `dependencies`) está documentada em:

- 📄 [ARCHITECTURE.md](ARCHITECTURE.md)


## Código e configuração

`src/routers/` define os endpoints, `src/schemas/` os contratos, `src/service/` coordena a entrada, `src/infra/` contém os clientes Redis/RabbitMQ e `src/dependencies.py` cria e fecha os clientes por requisição. A conexão RabbitMQ por requisição evita reutilizar canais ociosos encerrados pelo broker.

O Compose expõe a API na porta 8000 e carrega `.env` do serviço. Ajuste `RABBITMQ_*`, `REDIS_*`, `CONVERSATION_LOCK_TTL_SECONDS` e `QUEUE_MAX_MESSAGES` conforme o ambiente. `GET /docs` abre o OpenAPI.

~~~powershell
cd services/apis/py-agent-gateway-api
uv sync --frozen
uv run pytest tests
uv run ruff check src tests
~~~
