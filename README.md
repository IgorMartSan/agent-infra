# Agent Platform

Plataforma centralizada para receber mensagens de diferentes aplicações, processá-las com agentes de IA e devolver as respostas para o canal correto.

A ideia principal é permitir que aplicações como Django, sistemas internos, Google Chat, APIs externas e frontends web utilizem a mesma infraestrutura de agentes.

---

## 1. Objetivo

Criar uma API central de agentes que receba mensagens no formato padronizado:

```json
{
  "application_id": "erp",
  "user_id": "123",
  "chat_id": "456",
  "agent_id": "suporte",
  "message": "Verifique o chamado 900",
  "delivery": {
    "type": "WEBSOCKET",
    "target": "erp:chat:456"
  }
}
```

A plataforma deve:

1. receber a mensagem via FastAPI;
2. publicar a mensagem no RabbitMQ;
3. retornar `202 Accepted` após confirmação do broker;
4. consumir a mensagem em um worker;
5. encaminhá-la ao agente correto;
6. executar o agente;
7. salvar pergunta e resposta no PostgreSQL;
8. entregar a resposta pelo mecanismo configurado.

---

# 2. Arquitetura inicial

```text
                         CHANNELS
                            │
              Google / Web / APIs / etc
                            │
                            ▼
                       AGENT API
                         FastAPI
                            │
                            ▼
                        RabbitMQ
                     agent.inbound
                            │
                            ▼
                     ORCHESTRATOR
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
           Agent A       Agent B       Agent C
               │            │            │
               └────────────┼────────────┘
                            │
                            ▼
                       IA / Tools
                            │
                            ▼
                       PostgreSQL
                            │
                            ▼
                     DELIVERY SERVICE
                   /       /      \       \
                  ▼       ▼        ▼       ▼
             WebSocket   HTTP   Google   Outros
```

A primeira versão não precisa possuir uma segunda fila de saída.

O próprio worker, depois que o agente termina e salva a resposta, chama o `DeliveryService`.

---

# 3. Responsabilidade de cada componente

## FastAPI — Agent API

Responsável apenas pela entrada da plataforma.

Funções:

- receber a mensagem;
- validar o payload;
- gerar um `message_id`;
- publicar no RabbitMQ;
- aguardar `publisher confirm`;
- retornar `202 Accepted`.

A API **não deve esperar o agente terminar**.

Fluxo:

```text
Cliente
   │
   │ POST /v1/messages
   ▼
FastAPI
   │
   ▼
RabbitMQ
   │
   └── confirmou recebimento
            │
            ▼
       202 Accepted
```

Exemplo de resposta:

```json
{
  "message_id": "9d5fc9b0-1208-43fa-8f60-ec43e7db74b1",
  "status": "ACCEPTED"
}
```

Se o RabbitMQ estiver indisponível e não confirmar a publicação, a API deve retornar erro, por exemplo `503 Service Unavailable`.

---

# 4. RabbitMQ

O RabbitMQ funciona como fila de processamento.

Fila inicial:

```text
agent.inbound
```

Responsabilidades:

- absorver picos de requisições;
- desacoplar FastAPI da IA;
- manter mensagens enquanto os workers estão ocupados;
- permitir reentrega em caso de falha do worker.

Configuração recomendada para a primeira versão:

```text
Durable Queue
Persistent Messages
Publisher Confirms
Manual ACK
```

A mensagem só deve receber ACK depois que o processamento necessário estiver persistido com sucesso.

---

# 5. Contrato interno da mensagem

A mensagem publicada no RabbitMQ pode utilizar o seguinte formato:

```json
{
  "message_id": "uuid",
  "application_id": "erp",
  "user_id": "123",
  "chat_id": "456",
  "agent_id": "suporte",
  "message": "Verifique o chamado 900",
  "delivery": {
    "type": "WEBSOCKET",
    "target": "erp:chat:456"
  }
}
```

## Campos

### `message_id`

Identificador único da mensagem.

Deve ser criado antes da publicação no RabbitMQ.

Serve para:

- rastreamento;
- idempotência;
- evitar processamento duplicado;
- relacionar pergunta e resposta.

### `application_id`

Identifica a aplicação de origem.

Exemplos:

```text
erp
portal-rh
google-chat
sistema-financeiro
```

### `user_id`

Identifica o usuário dentro da aplicação de origem.

Pode ser `null` quando a aplicação trabalhar com uma conversa global.

### `chat_id`

Identifica o chat ou sessão dentro da aplicação.

Pode ser `null` quando a aplicação possuir somente uma conversa por usuário ou uma conversa global.

### `agent_id`

Define inicialmente qual agente deve receber a mensagem.

Exemplos:

```text
suporte
financeiro
rh
dados
```

No futuro, esse campo pode apontar para um orquestrador que decide dinamicamente qual agente executar.

### `message`

Texto enviado pelo usuário ou sistema.

### `delivery`

Define como a resposta deverá retornar.

---

# 6. Delivery

O `delivery` acompanha a mensagem desde a entrada, mas não participa do raciocínio do agente.

Exemplo WebSocket:

```json
{
  "delivery": {
    "type": "WEBSOCKET",
    "target": "erp:chat:456"
  }
}
```

Exemplo HTTP/Webhook:

```json
{
  "delivery": {
    "type": "HTTP",
    "target": "erp-callback"
  }
}
```

Exemplo Google Chat:

```json
{
  "delivery": {
    "type": "GOOGLE_CHAT",
    "target": "google-suporte",
    "metadata": {
      "space_id": "spaces/AAA",
      "thread_id": "spaces/AAA/threads/BBB"
    }
  }
}
```

É melhor utilizar um **destino lógico** em vez de aceitar URLs arbitrárias diretamente do cliente.

Por exemplo:

```text
erp-callback
```

é resolvido internamente para:

```text
https://erp.interno/api/agent/callback
```

Isso evita transformar a plataforma em um proxy HTTP aberto e facilita o gerenciamento de credenciais e endpoints.

---

# 7. Orchestrator

O `Orchestrator` é responsável por decidir qual agente executará a mensagem.

Fluxo:

```text
RabbitMQ
   │
   ▼
Orchestrator
   │
   ├── agent_id = suporte
   │        ↓
   │    SupportAgent
   │
   ├── agent_id = rh
   │        ↓
   │      RhAgent
   │
   └── agent_id = dados
            ↓
        DataAgent
```

Exemplo simplificado:

```python
class AgentRegistry:
    def __init__(self):
        self.agents = {
            "suporte": SupportAgent(),
            "rh": RhAgent(),
            "dados": DataAgent(),
        }

    def get(self, agent_id: str):
        return self.agents[agent_id]
```

```python
class Orchestrator:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def execute(self, message):
        agent = self.registry.get(message.agent_id)
        return agent.execute(message)
```

Inicialmente, o `agent_id` pode selecionar diretamente o agente.

No futuro, o Orchestrator pode tomar decisões mais avançadas.

---

# 8. Agent Worker

O worker consome `agent.inbound`.

Fluxo:

```text
RabbitMQ
   │
   ▼
Agent Worker
   │
   ▼
Orchestrator
   │
   ▼
Agent
   │
   ▼
PostgreSQL
   │
   ▼
DeliveryService
   │
   ▼
ACK RabbitMQ
```

Exemplo conceitual:

```python
def process_message(event):
    if already_processed(event.message_id):
        return

    response = orchestrator.execute(event)

    saved_response = repository.save_exchange(
        request=event,
        response=response,
    )

    delivery_service.deliver(
        original_message=event,
        response=saved_response,
    )
```

---

# 9. PostgreSQL

Na arquitetura inicial:

```text
FastAPI
   ↓
RabbitMQ
   ↓
Agent
   ↓
PostgreSQL
```

O PostgreSQL entra depois do processamento do agente.

Ele será responsável por armazenar:

- conversas;
- mensagens;
- respostas;
- status de processamento;
- informações necessárias para retry;
- histórico utilizado pelos agentes.

## Tabela `conversation`

```text
id UUID
application_id
user_id
chat_id
created_at
updated_at
```

Uma restrição lógica pode identificar uma conversa por:

```text
application_id + user_id + chat_id
```

Dependendo da aplicação, `user_id` e `chat_id` podem ser opcionais.

## Tabela `message`

```text
id UUID
conversation_id
external_message_id
agent_id
role
content
status
created_at
```

Exemplo:

```text
role = USER
role = ASSISTANT
role = SYSTEM
```

## Tabela `delivery`

```text
id UUID
message_id
type
target
status
attempts
last_error
sent_at
created_at
```

Status iniciais:

```text
PENDING
SENDING
SENT
FAILED
```

---

# 10. Idempotência

Como o RabbitMQ pode reenviar mensagens, o processamento deve ser idempotente.

Exemplo:

```text
RabbitMQ
   ↓
message_id = ABC
   ↓
Agent terminou
   ↓
PostgreSQL salvou
   ↓
worker caiu antes do ACK
```

O RabbitMQ pode entregar novamente:

```text
message_id = ABC
```

Antes de executar o agente novamente:

```python
if repository.exists_message(message_id):
    # já processada
    return
```

O banco deve possuir uma restrição `UNIQUE` para o identificador usado na deduplicação.

---

# 11. Delivery Service

O agente não conhece Google, WebSocket, HTTP ou outros canais.

Ele retorna apenas a resposta.

```python
response = agent.execute(message)
```

Depois:

```python
delivery_service.deliver(message, response)
```

O `DeliveryService` seleciona o sender correto.

```python
class DeliveryService:
    def __init__(self, senders):
        self.senders = senders

    def deliver(self, message, response):
        sender = self.senders[message.delivery.type]
        sender.send(message.delivery, response)
```

Registro inicial:

```python
senders = {
    "WEBSOCKET": WebSocketSender(),
    "HTTP": HttpSender(),
    "GOOGLE_CHAT": GoogleChatSender(),
}
```

---

# 12. WebSocket Gateway próprio

A plataforma pode possuir um serviço central de WebSocket.

```text
                    Realtime Gateway
                  wss://realtime.local
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
         App Web A    App Web B    App Web C
```

Cada aplicação web vira apenas cliente dessa infraestrutura.

Ela precisa saber:

```text
URL do WebSocket
Token de autenticação
Canal que pode assinar
```

Exemplo:

```javascript
const socket = new WebSocket(
    "wss://realtime.exemplo/ws"
)
```

Depois da autenticação:

```json
{
  "type": "SUBSCRIBE",
  "channel": "erp:chat:456"
}
```

Quando o agente responder:

```text
DeliveryService
      │
      ▼
WebSocketSender
      │
      ▼
Realtime Gateway
      │
      ▼
erp:chat:456
      │
      ▼
Browser
```

O WebSocket é responsável por **tempo real**, não por persistência.

Se o usuário estiver offline, a resposta continua salva no PostgreSQL.

Quando ele voltar, a aplicação recupera o histórico pela API e usa o WebSocket somente para as mensagens novas.

---

# 13. HTTP / Webhook

Quando a aplicação de origem for outro backend, a resposta pode ser enviada por HTTP.

Exemplo:

```text
Agent
   ↓
PostgreSQL
   ↓
DeliveryService
   ↓
HttpSender
   ↓
POST ERP /callback
```

Payload:

```json
{
  "message_id": "response-123",
  "request_message_id": "request-100",
  "chat_id": "456",
  "content": "Seu chamado foi localizado"
}
```

O endpoint real deve preferencialmente ser configurado pela plataforma.

```text
application_id = erp

target = erp-callback

        ↓

https://erp.interno/api/agent/callback
```

---

# 14. Google Chat

Para Google Chat, o `DeliveryService` utiliza um `GoogleChatSender`.

```text
Agent
   ↓
DeliveryService
   ↓
GoogleChatSender
   ↓
Google Chat API
   ↓
Google Chat
```

A mensagem de entrada precisa carregar ou permitir recuperar dados como:

```text
space_id
thread_id
```

O agente não precisa conhecer esses detalhes.

---

# 15. Estratégia de ACK

A estratégia inicial será:

```text
FastAPI
   ↓
RabbitMQ
   ↓
Publisher Confirm
   ↓
202 Accepted
```

No consumidor:

```text
RabbitMQ
   ↓
Agent Worker
   ↓
Agent executa
   ↓
PostgreSQL salva
   ↓
Delivery tenta enviar
   ↓
ACK
```

Para um MVP, isso é simples.

Porém, existe uma consideração importante: se o envio externo estiver indisponível por muito tempo, não é desejável manter a mensagem RabbitMQ presa indefinidamente.

Por isso, a primeira evolução natural será persistir o estado de entrega e permitir retry independente.

---

# 16. Clean Architecture simplificada

Estrutura recomendada:

```text
app/
│
├── main.py
│
├── api/
│   ├── routes/
│   │   └── messages.py
│   └── schemas/
│       └── messages.py
│
├── domain/
│   ├── entities/
│   │   ├── message.py
│   │   ├── conversation.py
│   │   └── delivery.py
│   │
│   └── interfaces/
│       ├── message_repository.py
│       ├── agent.py
│       └── sender.py
│
├── application/
│   ├── receive_message.py
│   ├── process_message.py
│   ├── orchestrator.py
│   └── delivery_service.py
│
├── infrastructure/
│   ├── database/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── repositories.py
│   │
│   ├── messaging/
│   │   ├── rabbitmq.py
│   │   ├── publisher.py
│   │   └── consumer.py
│   │
│   ├── agents/
│   │   ├── support_agent.py
│   │   ├── rh_agent.py
│   │   └── data_agent.py
│   │
│   └── delivery/
│       ├── websocket_sender.py
│       ├── http_sender.py
│       └── google_chat_sender.py
│
└── workers/
    └── agent_worker.py
```

## Regra mental

```text
API
↓
recebe / valida HTTP

Application
↓
coordena os casos de uso

Domain
↓
representa conceitos e contratos

Infrastructure
↓
RabbitMQ / PostgreSQL / HTTP / Google / WebSocket
```

---

# 17. Fluxo completo de uma mensagem WebSocket

```text
Browser
   │
   │ POST /v1/messages
   ▼
FastAPI
   │
   │ publish
   ▼
RabbitMQ
   │
   │ publisher confirm
   ▼
202 Accepted

Enquanto isso:

RabbitMQ
   │
   ▼
Agent Worker
   │
   ▼
Orchestrator
   │
   ▼
SupportAgent
   │
   ▼
IA
   │
   ▼
PostgreSQL
   │
   ▼
DeliveryService
   │
   ▼
WebSocketSender
   │
   ▼
Realtime Gateway
   │
   ▼
channel = erp:chat:456
   │
   ▼
Browser
```

---

# 18. Fluxo completo de uma mensagem HTTP

```text
ERP
 │
 │ POST /v1/messages
 ▼
FastAPI
 │
 ▼
RabbitMQ
 │
 ▼
Agent Worker
 │
 ▼
Agent
 │
 ▼
PostgreSQL
 │
 ▼
DeliveryService
 │
 ▼
HttpSender
 │
 │ POST /agent/callback
 ▼
ERP
```

---

# 19. Fluxo completo Google Chat

```text
Google Chat
     │
     │ evento HTTP
     ▼
Google Adapter
     │
     ▼
Agent API
     │
     ▼
RabbitMQ
     │
     ▼
Agent Worker
     │
     ▼
Agent
     │
     ▼
PostgreSQL
     │
     ▼
DeliveryService
     │
     ▼
GoogleChatSender
     │
     ▼
Google Chat API
     │
     ▼
Google Chat
```

---

# 20. Segurança

## Autenticação da Agent API

Cada aplicação deve possuir credenciais próprias.

O `application_id` informado no payload não deve ser suficiente para autenticar uma aplicação.

Possibilidades:

```text
JWT
API Key
OAuth2
mTLS
```

Para o MVP, uma API Key por aplicação pode ser suficiente.

## Delivery HTTP

Nunca permitir que qualquer usuário informe uma URL arbitrária para o backend chamar.

Preferir:

```json
{
  "delivery": {
    "type": "HTTP",
    "target": "erp-callback"
  }
}
```

em vez de:

```json
{
  "delivery": {
    "type": "HTTP",
    "url": "https://qualquer-site.com"
  }
}
```

## WebSocket

O usuário só pode assinar canais para os quais possui autorização.

Nunca confiar apenas em:

```text
SUBSCRIBE erp:chat:456
```

O gateway deve validar o token e as permissões antes de adicionar a conexão ao canal.

---

# 21. MVP recomendado

Começar somente com:

```text
FastAPI
RabbitMQ
PostgreSQL
1 Agent Worker
1 Agent
HTTP Delivery
```

Fluxo:

```text
POST /messages
      ↓
RabbitMQ
      ↓
Agent Worker
      ↓
Agent
      ↓
PostgreSQL
      ↓
HTTP callback
```

Depois adicionar:

```text
WebSocket Gateway
Google Chat
mais agentes
mais workers
retry avançado
observabilidade
```

---

# 22. Ordem de implementação

## Fase 1 — Agent API

Criar:

```text
POST /v1/messages
GET /health
```

Validar o contrato da mensagem e publicar no RabbitMQ.

## Fase 2 — RabbitMQ

Criar:

```text
agent.inbound
```

Configurar:

```text
durable queue
persistent message
publisher confirms
manual ACK
```

## Fase 3 — Worker

Criar consumidor de `agent.inbound`.

Inicialmente apenas imprimir:

```text
message_id
application_id
agent_id
message
```

## Fase 4 — Orchestrator

Criar:

```text
AgentRegistry
Orchestrator
```

Inicialmente:

```text
agent_id → Agent
```

## Fase 5 — Primeiro agente

Criar um `EchoAgent` ou `SupportAgent` simples.

Exemplo:

```python
class EchoAgent:
    def execute(self, message):
        return f"Agente recebeu: {message.message}"
```

Antes de conectar qualquer LLM.

## Fase 6 — PostgreSQL

Criar:

```text
conversation
message
delivery
```

Salvar pergunta e resposta.

## Fase 7 — HTTP Delivery

Criar primeiro `HttpSender`.

Testar ponta a ponta:

```text
Cliente
→ Agent API
→ RabbitMQ
→ Agent
→ PostgreSQL
→ HTTP Callback
```

## Fase 8 — IA local

Substituir `EchoAgent` por um agente que utilize seu runtime de IA local.

## Fase 9 — WebSocket Gateway

Criar infraestrutura própria de realtime.

Contrato mínimo:

```text
AUTH
SUBSCRIBE
UNSUBSCRIBE
EVENT
PING
PONG
ERROR
```

## Fase 10 — Google Chat

Adicionar adapter de entrada e `GoogleChatSender`.

---

# 23. Princípios da arquitetura

## RabbitMQ é transporte

```text
RabbitMQ
= mensagem aguardando processamento
```

## PostgreSQL é histórico e estado

```text
PostgreSQL
= conversa, mensagens e resultados
```

## WebSocket é realtime

```text
WebSocket
= notificação para clientes conectados
```

## Delivery é integração

```text
Delivery
= como a resposta sai da plataforma
```

## Agent é regra inteligente

```text
Agent
= entende a solicitação e produz a resposta
```

## Orchestrator escolhe quem trabalha

```text
Orchestrator
= decide qual agente executar
```

---

# 24. Visão final do projeto

```text
                            ┌─────────────────────┐
                            │      CLIENTES       │
                            │                     │
                            │ Django / React      │
                            │ Google Chat         │
                            │ ERP / APIs          │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │      FastAPI        │
                            │      Agent API      │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │      RabbitMQ       │
                            │   agent.inbound     │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │    Agent Worker     │
                            │    Orchestrator     │
                            └──────────┬──────────┘
                                       │
                         ┌─────────────┼─────────────┐
                         ▼             ▼             ▼
                     Agent A       Agent B       Agent C
                         │             │             │
                         └─────────────┼─────────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │      IA / Tools     │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │     PostgreSQL      │
                            │ conversations       │
                            │ messages            │
                            │ deliveries          │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │  Delivery Service   │
                            └──────────┬──────────┘
                                       │
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
                 WebSocket           HTTP          Google Chat
                     │                 │                 │
                     ▼                 ▼                 ▼
                 Frontend           Backend             User
```

---

# 25. Primeira meta

Não começar pela IA.

A primeira meta deve ser fazer funcionar este caminho:

```text
POST /v1/messages
        ↓
RabbitMQ
        ↓
Worker
        ↓
EchoAgent
        ↓
PostgreSQL
        ↓
HTTP Callback
```

Quando esse fluxo estiver confiável, substituir o `EchoAgent` pelo primeiro agente real.

Isso permite validar primeiro a infraestrutura de mensageria, persistência e entrega antes de adicionar a complexidade do modelo de IA.
---

# 26. Como testar o fluxo completo

O fluxo implementado atualmente é:

```text
Chat CLI
  -> Agent API (FastAPI, porta 8000)
  -> RabbitMQ (exchange agent.requests, routing key agent.simple)
  -> Worker (LangGraph)
  -> Redis Pub/Sub (canal chat:response:{application_id}:{chat_id})
  -> Chat CLI exibe a resposta
```

## Subir a infraestrutura com Docker Compose

Na raiz do projeto:

```bash
docker compose -p agent_module_with_redis \
  -f composes/compose.rabbitmq.yaml \
  -f composes/compose.redis.yaml \
  -f composes/compose.postgres.yaml \
  -f composes/compose.services.yaml \
  up -d rabbitmq redis postgres-vector py-agent-gateway-api worker-agent
```

Portas expostas no host:

| Porta | Serviço |
|-------|---------|
| 8000 | Agent API (Swagger em `/docs`) |
| 5673 | RabbitMQ (AMQP; management UI em 15673, usuário `admin` / senha `admin123`) |
| 6380 | Redis |
| 5433 | PostgreSQL |

> As portas 5673/6380 evitam conflito com outros stacks que usem as portas padrão 5672/6379.

Se o código do worker ou da API mudar, rebuild antes:

```bash
docker compose -p agent_module_with_redis \
  -f composes/compose.rabbitmq.yaml \
  -f composes/compose.redis.yaml \
  -f composes/compose.postgres.yaml \
  -f composes/compose.services.yaml \
  build worker-agent py-agent-gateway-api
```

## Rodar o chat CLI

O chat publica a mensagem via API, fica travado esperando a resposta no Redis Pub/Sub e exibe quando chegar.

```bash
cd services/jobs/py-simple-agent-job
REDIS_PORT=6380 .venv/Scripts/python.exe chat.py
```

(Linux/macOS: `REDIS_PORT=6380 .venv/bin/python chat.py`)

Exemplo de sessão:

```text
voce > olá, tudo bem?
aguardando resposta...
agente > Eu sou o Simple Agent. ... Eu recebi a mensagem: olá, tudo bem?
```

## Testar a API manualmente (sem chat)

```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "application_id": "test-app",
    "chat_id": "chat-1",
    "agent_id": "simple-agent",
    "message": "Verifique o status do chamado 900."
  }'
```

Resposta esperada:

```json
{
  "message_id": "9d5fc9b0-1208-43fa-8f60-ec43e7db74b1",
  "status": "ACCEPTED"
}
```

Para ver a resposta do agente fora do chat CLI, assine o canal correspondente:

```bash
docker exec -it agent_module_with_redis-redis-1 redis-cli SUBSCRIBE "chat:response:test-app:chat-1"
```

## Desenvolvimento local (sem Docker)

```bash
cd services/jobs/py-simple-agent-job
uv sync
RABBITMQ_HOST=localhost RABBITMQ_USER=admin RABBITMQ_PASSWORD=admin123 \
RABBITMQ_PORT=5673 uv run python src/main.py
```

Documentação detalhada de cada serviço nos respectivos `README.md`:

- `services/apis/py-agent-gateway-api/README.md`
- `services/jobs/py-simple-agent-job/README.md`
- `services/jobs/py-message-delivery/README.md` 
