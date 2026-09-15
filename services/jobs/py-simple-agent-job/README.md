# Simple Agent Job

## Descrição
Worker que consome mensagens do RabbitMQ, processa através de um agente de IA e publica a resposta via **Redis Pub/Sub**. Não utiliza filas de saída no RabbitMQ — toda a entrega da resposta é feita exclusivamente pelo Redis Pub/Sub.

## Responsabilidades
- Consumir mensagens da fila RabbitMQ configurada
- Processar cada mensagem através do grafo do agente (LangGraph)
- Publicar respostas completas via **Redis Pub/Sub** para entrega aos clientes
- Reconectar automaticamente em caso de falha no RabbitMQ

## Contrato de Entrada

**Fonte:** Fila RabbitMQ (`RABBITMQ_QUEUE`, padrão: `agent.simple.requests`)

**Payload esperado:**
```json
{
  "message_id": "uuid",              // Identificador único da mensagem
  "application_id": "string",        // Identificador da aplicação origem
  "user_id": "string?",              // Identificador do usuário
  "chat_id": "string?",              // Identificador do chat/conversa
  "agent_id": "string",              // Identificador do agente
  "message": "string",               // Conteúdo a ser processado (obrigatório, não vazio)
  "metadata": "object?",             // Metadados opcionais
  "delivery": "object?"              // Configuração de entrega da resposta
}
```

## Contrato de Saída

**Destino:** **Redis Pub/Sub** (canal prefixado por `REDIS_RESPONSE_CHANNEL_PREFIX`, padrão: `chat:response`)

**Evento publicado:**
```json
{
  "type": "message.completed",
  "application_id": "string",
  "conversation_id": "string",       // Derivado de chat_id ou conversation_id
  "message_id": "uuid",
  "agent_id": "string",
  "content": "string"                // Resposta gerada pelo agente
}
```

**Canal Redis:** O canal é construído como `chat:response:{application_id}:{conversation_id}` usando URL encoding para os identificadores.

**Subscribers:** O método `publish_completed` retorna o número de subscribers que receberam a mensagem.

## Configuração (Variáveis de Ambiente)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `AGENT_ID` | `simple-agent` | Identificador do agente |
| `RABBITMQ_EXCHANGE` | `agent.requests` | Exchange do RabbitMQ |
| `RABBITMQ_QUEUE` | `agent.simple.requests` | Fila de consumo |
| `RABBITMQ_ROUTING_KEY` | `agent.simple` | Routing key |
| `RABBITMQ_PREFETCH_COUNT` | `1` | Prefetch count do RabbitMQ |
| `RABBITMQ_RECONNECT_DELAY` | `3` | Delay em segundos para reconexão |
| `REDIS_RESPONSE_CHANNEL_PREFIX` | `chat:response` | Prefixo do canal Redis Pub/Sub |
| `LOG_LEVEL` | `INFO` | Nível de log |

## Arquitetura de Entrega

Este serviço **não utiliza filas de saída no RabbitMQ**. A resposta do agente é publicada diretamente no Redis Pub/Sub, onde os clientes (aplicações frontend, websockets, etc.) se inscrevem para receber as respostas em tempo real.

Fluxo:
1. Mensagem chega via RabbitMQ (fila de entrada)
2. Agente processa a mensagem (LangGraph)
3. Resposta é publicada no Redis Pub/Sub
4. Subscribers recebem a resposta instantaneamente

## Tecnologias
- Python 3.10+
- LangGraph (grafo do agente)
- RabbitMQ (Pika) — apenas para consumo de mensagens
- Redis (Pub/Sub) — apenas para publicação de respostas
- python-dotenv