# Padrão dos Agent Workers

Cada agente deve ser um job independente e autocontido. O RabbitMQ escolhe o worker por `routing_key`; nenhum worker deve possuir um `if/elif` ou registry central para selecionar agentes.

O `py-simple-agent-job` é a implementação de referência.

## Estrutura

```text
py-<nome>-agent-job/
├── src/
│   ├── main.py
│   ├── processor.py
│   ├── test_main.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── state.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── system_prompt.py
│   ├── tools/
│   │   └── __init__.py
│   └── infra/
│       ├── rabbitmq/
│       ├── redis/
│       └── postgresql/
├── tests/
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── README.md
```

## Responsabilidades

- `main.py`: configura conexões, consome a fila exclusiva do agente, coordena o processamento e publica o evento final.
- `processor.py`: valida o payload, executa o grafo local e devolve a resposta, sem conhecer RabbitMQ ou Redis.
- `graph/`: contém apenas o estado, os nós e a montagem do LangGraph daquele agente.
- `prompts/`: contém apenas os prompts daquele agente.
- `tools/`: contém apenas as ferramentas daquele agente.
- `infra/rabbitmq/`: conexão e consumo da fila de entrada.
- `infra/redis/`: publicação do evento final `message.completed`.
- `infra/postgresql/`: persistência do agente quando essa etapa for implementada.
- `test_main.py`: executa o mesmo `processor.py` pelo console, sem RabbitMQ ou Redis.

## Configuração por agente

Todos os agentes compartilham o exchange `agent.requests`, mas cada agente possui sua própria identidade, routing key e fila.

Exemplo do Simple Agent:

```env
AGENT_ID=simple-agent
RABBITMQ_EXCHANGE=agent.requests
RABBITMQ_ROUTING_KEY=agent.simple
RABBITMQ_QUEUE=agent.simple.requests
```

Exemplo de um futuro Support Agent:

```env
AGENT_ID=support-agent
RABBITMQ_EXCHANGE=agent.requests
RABBITMQ_ROUTING_KEY=agent.support
RABBITMQ_QUEUE=agent.support.requests
```

## Fluxo comum

```text
Gateway API
    ↓ agent_id
Exchange agent.requests
    ↓ routing key exclusiva
Fila exclusiva do agente
    ↓
main.py
    ↓
processor.py
    ↓
LangGraph do agente
    ↓
Persistência PostgreSQL (planejada)
    ↓
Redis Pub/Sub: message.completed
    ↓
ACK no RabbitMQ
```

## Criação de um novo agente

1. Copie a estrutura do `py-simple-agent-job` para um novo job.
2. Defina um novo `AGENT_ID`, `RABBITMQ_ROUTING_KEY` e `RABBITMQ_QUEUE`.
3. Altere somente o conteúdo específico em `graph/`, `prompts/` e `tools/`.
4. Mantenha o contrato de entrada recebido do Gateway.
5. Mantenha o evento final `message.completed` com os identificadores originais.
6. Adicione o novo worker ao Docker Compose com suas próprias variáveis.
7. Execute os testes do novo job antes de adicioná-lo ao fluxo.

