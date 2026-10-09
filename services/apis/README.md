# Serviços de API (`services/apis/`)

Serviços HTTP sem estado (stateless) para recepção, validação rápida (fail-fast) e roteamento de tráfego de entrada.

## Serviços Existentes:
- **[`py-agent-gateway-api`](py-agent-gateway-api/README.md):** Gateway FastAPI que recebe requisições, gerencia locks distribuídos de conversa no Redis, valida limites de fila e publica mensagens no broker RabbitMQ.

## Arquitetura Obrigatória:
Consulte [`ARCHITECTURE.md`](../../ARCHITECTURE.md#31-padrão-1-apis-fastapi-servicesapisapi-name) e [`py-agent-gateway-api/ARCHITECTURE.md`](py-agent-gateway-api/ARCHITECTURE.md) para detalhes da estrutura `routers`, `schemas`, `service`, `infra` e `dependencies`.
