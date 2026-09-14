# Simple Agent

O **Simple Agent** é um agente simples criado com **LangGraph** para testar a estrutura básica de um agente.

## Execução

O fluxo de entrada usa um exchange `direct` e uma fila exclusiva deste agente. A fila de saída existente foi preservada:

```text
Agent Gateway API
  -> exchange agent.requests
  -> routing key agent.simple
  -> queue agent.simple.requests
  -> Simple Agent Worker
  -> agent.outbound
```

Na pasta deste job, instale as dependências e inicie o worker:

```powershell
uv sync
uv run python src/main.py
```

O processo permanece aguardando mensagens sem fazer polling contínuo. Para testar apenas o agente no terminal, sem RabbitMQ:

```powershell
uv run python src/test_main.py
```

Use `sair`, `exit` ou `quit` para encerrar o teste local.

As principais configurações do worker são:

```text
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=admin123
RABBITMQ_VHOST=/
AGENT_ID=simple-agent
RABBITMQ_EXCHANGE=agent.requests
RABBITMQ_QUEUE=agent.simple.requests
RABBITMQ_ROUTING_KEY=agent.simple
RABBITMQ_OUTBOUND_QUEUE=agent.outbound
RABBITMQ_PREFETCH_COUNT=1
```

Ele recebe uma mensagem e retorna:

```text
Eu recebi a mensagem: <mensagem enviada>
```

Exemplo:

```text
Entrada:
Olá

Saída:
Eu recebi a mensagem: Olá
```

## Arquitetura

```text
simple-agent/
├── src/
│   └── simple_agent/
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── graph.py
│       │   ├── state.py
│       │   └── nodes.py
│       │
│       ├── prompts/
│       │   ├── __init__.py
│       │   └── system_prompt.py
│       │
│       └── tools/
│           └── __init__.py
│
├── main.py
└── pyproject.toml
```

### `graph/`

Contém o fluxo do agente.

```text
graph.py  → cria e compila o grafo do LangGraph
state.py  → define os dados que passam pelo grafo
nodes.py  → contém as funções executadas pelo grafo
```

Fluxo atual:

```text
START
  ↓
receive_message
  ↓
END
```

### `prompts/`

Contém os prompts e instruções do agente.

```text
system_prompt.py
```

Atualmente define a identificação do agente, por exemplo:

```text
Eu sou o Simple Agent.
Sou um agente simples criado para testar o funcionamento do LangGraph.
```

### `tools/`

Contém as ferramentas que poderão ser utilizadas pelo agente.

Atualmente o agente ainda não possui tools, mas a pasta já existe para futuras implementações.

### `main.py`

É o ponto de entrada para executar e testar o agente.

O fluxo completo é:

```text
Mensagem
   ↓
main.py
   ↓
LangGraph
   ↓
AgentState
   ↓
receive_message
   ↓
Resposta
```

## O que o agente faz

Nesta primeira versão, o Simple Agent:

* recebe uma mensagem;
* executa essa mensagem através de um grafo LangGraph;
* adiciona a identificação do agente;
* retorna a mensagem recebida.

Ele ainda não utiliza LLM.

A finalidade atual é apenas validar a arquitetura básica do LangGraph antes de adicionar modelos, tools e integrações externas.
