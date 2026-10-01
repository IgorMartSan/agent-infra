# Arquivos Compose

`docker-compose.yml` inclui `compose.postgres.yaml`, `compose.redis.yaml`, `compose.rabbitmq.yaml` e `compose.services.yaml`. Este é o conjunto padrão da aplicação. Os demais arquivos nesta pasta são stacks auxiliares e não iniciam com o comando principal.

| Serviço | Porta no host |
| --- | --- |
| Chat Next.js | 3001 |
| Gateway FastAPI | 8000 |
| Redis | 6380 |
| Redis Insight | 50030 |
| RabbitMQ AMQP / painel | 5673 / 15673 |
| PostgreSQL `postgres-vector` / pgAdmin | 5433 / 5434 |

Dentro da rede Compose, os serviços usam `redis:6379`, `rabbitmq:5672` e os nomes internos dos containers. O `agent-rsa` alcança um PostgreSQL do host por `host.docker.internal`. `agent-argus` usa os parâmetros SQL carregados de `services/jobs/py-agent-job/.env.argus`.

`compose.qdrant.yaml`, `compose.n8n.yaml`, `compose.phoenix.yaml`, `compose.llms.yaml` e `compose.infra.yaml` são opcionais. As pastas `compose-agent/` e `compose-langfuse/` também contêm stacks próprias. Revise portas, volumes e credenciais antes de iniciá-las de forma independente.
