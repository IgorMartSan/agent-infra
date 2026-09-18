# Agent Gateway API

## Descrição
API FastAPI responsável por receber mensagens de diferentes aplicações e encaminhá-las para processamento assíncrono através do RabbitMQ. Atua como gateway centralizado para comunicação com agentes de IA.

## Responsabilidades
- Receber mensagens de aplicações clientes
- Publicar mensagens no RabbitMQ para processamento assíncrono
- Retornar confirmação imediata após aceitar a mensagem
- Gerenciar conexões com RabbitMQ

## Contrato de Entrada

### Endpoint: `POST /api/v1/messages`

**Request Body:**
```json
{
  "application_id": "string",        // Identificador da aplicação de origem (ex: "erp")
  "user_id": "string?",              // Identificador do usuário na aplicação origem
  "chat_id": "string?",              // Identificador do chat/conversa
  "agent_id": "string",              // Identificador do agente que processará a mensagem
  "message": "string",               // Conteúdo enviado para o agente
  "metadata": "object?",             // Metadados opcionais da aplicação origem
  "delivery": {                      // Configuração de entrega da resposta
    "type": "WEBSOCKET | HTTP | GOOGLE_CHAT | NONE",
    "target": "string?",             // Destino lógico para entregas HTTP
    "channel": "string?",            // Canal para entrega via WebSocket
    "space_id": "string?"            // Identificador do espaço do Google Chat
  }
}
```

## Contrato de Saída

**Response (202 Accepted):**
```json
{
  "message_id": "uuid",              // Identificador único da mensagem
  "status": "ACCEPTED"               // Status inicial da mensagem
}
```

**Respostas de Erro:**
- `422`: Payload inválido
- `503`: RabbitMQ indisponível

## Endpoints Adicionais
- `GET /` - Verificar status da API
- `GET /docs` - Documentação Swagger UI
- `GET /redoc` - Documentação ReDoc

## Tecnologias
- FastAPI
- RabbitMQ (Pika)
- Pydantic
- Uvicorn