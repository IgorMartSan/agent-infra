# Message Delivery Job

## Descrição
Worker que consome mensagens do RabbitMQ, processa através de um agente e publica a resposta em outra fila RabbitMQ para entrega downstream. Diferente do Simple Agent Job, este serviço mantém todo o fluxo dentro do RabbitMQ (sem Redis Pub/Sub).

## Responsabilidades
- Consumir mensagens da fila de entrada do RabbitMQ
- Processar cada mensagem através do processador do agente
- Publicar respostas processadas em uma fila de saída (outbound queue)
- Reconectar automaticamente em caso de falha no RabbitMQ

## Contrato de Entrada

**Fonte:** Fila RabbitMQ de entrada (`RABBITMQ_QUEUE`, padrão: `agent.simple.requests`)

**Payload esperado:**
```json
{
  "message_id": "uuid",              // Identificador único da mensagem
  "application_id": "string",        // Identificador da aplicação origem
  "user_id": "string?",              // Identificador do usuário
  "chat_id": "string?",              // Identificador do chat/conversa
  "agent_id": "string",              // Identificador do agente
  "message": "string",               // Conteúdo a ser processado (obrigatório, não vazio)
  "metadata": "object?"              // Metadados opcionais
}
```

## Contrato de Saída

**Destino:** Fila RabbitMQ de saída (`RABBITMQ_OUTBOUND_QUEUE`, padrão: `agent.outbound`)

**Resposta publicada:**
```json
{
  "message_id": "uuid",
  "application_id": "string",
  "agent_id": "string",
  "status": "PROCESSED",
  "response": "string"               // Resposta gerada pelo processador
}
```

## Configuração (Variáveis de Ambiente)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `AGENT_ID` | `simple-agent` | Identificador do agente |
| `RABBITMQ_EXCHANGE` | `agent.requests` | Exchange do RabbitMQ |
| `RABBITMQ_QUEUE` | `agent.simple.requests` | Fila de entrada (consumo) |
| `RABBITMQ_ROUTING_KEY` | `agent.simple` | Routing key de entrada |
| `RABBITMQ_OUTBOUND_QUEUE` | `agent.outbound` | Fila de saída (respostas) |
| `RABBITMQ_PREFETCH_COUNT` | `1` | Prefetch count do RabbitMQ |
| `RABBITMQ_RECONNECT_DELAY` | `3` | Delay em segundos para reconexão |
| `LOG_LEVEL` | `INFO` | Nível de log |

## Tecnologias
- Python 3.10+
- RabbitMQ (Pika)
- python-dotenv