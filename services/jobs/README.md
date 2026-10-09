# Serviços de Jobs e Workers (`services/jobs/`)

Processos de processamento em segundo plano que consomem filas assíncronas do RabbitMQ e orquestram fluxos de agentes inteligentes.

## Serviços Existentes:
- **[`py-agent-job`](py-agent-job/README.md):** Worker unificado de agentes LangGraph/LangChain. Consome tarefas do broker, executa grafos de decisão, acessa ferramentas e publica resultados ou erros no Redis Pub/Sub.

## Arquitetura Obrigatória:
Consulte [`ARCHITECTURE.md`](../../ARCHITECTURE.md#32-padrão-2-workers-de-agentes-servicesjobspy-agent-job) e [`py-agent-job/ARCHITECTURE.md`](py-agent-job/ARCHITECTURE.md) para o padrão modular de agentes (`model.py`, `graph/`, `prompts/`, `tools/`).
