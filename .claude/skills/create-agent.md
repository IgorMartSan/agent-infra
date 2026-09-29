---
name: create-agent
description: Cria um novo agente LangChain no py-agent-job seguindo a arquitetura padronizada de pastas, env e Docker Compose.
---

# Skill: Criar Novo Agente (py-agent-job)

Use este skill sempre que o usuário pedir para criar um novo agente dentro do módulo `services/jobs/py-agent-job`.

## Estrutura de Pastas Obrigatória

Todo agente LangChain deve residir em:
```
services/jobs/py-agent-job/src/agents/langchain_agents/<nome_do_agente>/
```

Dentro da pasta do agente, crie exatamente esta estrutura:
```
<nome_do_agente>/
├── __init__.py              # Docstring descrevendo o agente
├── model.py                 # get_chat_model() com @lru_cache
├── graph/
│   ├── __init__.py          # Exporta `graph` compilado
│   ├── state.py             # AgentState(TypedDict)
│   ├── nodes.py             # Funções dos nós (ex: receive_message)
│   └── graph.py             # StateGraph compilado
└── prompts/
    ├── __init__.py          # Exporta SYSTEM_PROMPT
    └── system_prompt.py     # String do prompt do sistema
```

**Regras de nomenclatura:**
- Nome da pasta: `snake_case` (ex: `sql_agent`, `customer_support_agent`)
- O nome da pasta será usado nos imports Python
- O `AGENT_ID` no `.env` pode usar hífen (ex: `sql-agent`), mas a pasta deve ser `sql_agent`

## Arquivos Modelo

### `__init__.py` (raiz do agente)
```python
"""Agente <Nome>: <descrição curta do propósito>."""
```

### `model.py`
```python
import os
from functools import lru_cache
from langchain_openai import ChatOpenAI


@lru_cache(maxsize=1)
def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gemma4"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8072/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "EMPTY"),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
        timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120")),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
    )
```

### `graph/state.py`
```python
from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    message: str
    response: str
    thread_id: NotRequired[str]
```

### `prompts/system_prompt.py`
```python
SYSTEM_PROMPT = """
<Instruções específicas do agente aqui>.
Responda sempre em português do Brasil, de forma clara e objetiva.
""".strip()
```

### `graph/nodes.py`
```python
import logging
import os
from uuid import uuid4
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from agents.langchain_agents.<nome>.graph.state import AgentState
from agents.langchain_agents.<nome>.prompts.system_prompt import SYSTEM_PROMPT
from agents.langchain_agents.<nome>.model import get_chat_model

logger = logging.getLogger(__name__)

async def receive_message(state: AgentState) -> dict:
    # Se usar MCP tools:
    server_path = os.getenv("MCP_SERVER_PATH")
    if server_path:
        mcp_config = {
            os.getenv("MCP_SERVER_NAME", "mcp"): {
                "command": "python",
                "args": [server_path],
                "transport": "stdio",
            }
        }
        client = MultiServerMCPClient(mcp_config)
        tools = await client.get_tools()
    else:
        tools = []

    agent = create_react_agent(
        model=get_chat_model(),
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": state["message"]}]},
        config={
            "recursion_limit": int(os.getenv("AGENT_RECURSION_LIMIT", "12")),
            "configurable": {"thread_id": state.get("thread_id") or uuid4().hex},
        },
    )
    last = result["messages"][-1]
    content = getattr(last, "content", str(last))
    return {"response": content.strip() if isinstance(content, str) else str(content).strip()}
```

### `graph/graph.py`
```python
from langgraph.graph import END, START, StateGraph
from agents.langchain_agents.<nome>.graph.nodes import receive_message
from agents.langchain_agents.<nome>.graph.state import AgentState

builder = StateGraph(AgentState)
builder.add_node("receive_message", receive_message)
builder.add_edge(START, "receive_message")
builder.add_edge("receive_message", END)
graph = builder.compile()
```

### `graph/__init__.py`
```python
from .graph import graph

__all__ = ["graph"]
```

## Integração no main.py

Após criar a pasta do agente, adicione o import e a entrada no dicionário `AGENTS` em `src/main.py`:

```python
from agents.langchain_agents.<nome>.graph import graph as <nome>_graph

AGENTS = {
    "rsa-agent": rsa_graph,
    "<agent-id>": <nome>_graph,  # ← nova linha
}
```

**Importante:** A chave no dicionário `AGENTS` é o `AGENT_ID` (pode ter hífen). O import usa o nome da pasta (snake_case).

## Configuração de Ambiente (.env)

### Arquivo específico do agente
Crie `services/jobs/py-agent-job/.env.<nome>` com **apenas**:
```env
# Configuração específica do Agente <Nome>
AGENT_ID=<agent-id>
RABBITMQ_QUEUE=agent.<nome>.requests
RABBITMQ_ROUTING_KEY=agent.<nome>
```

**NÃO inclua** nestes arquivos:
- Variáveis de infra (Redis, RabbitMQ host/port) → ficam no `.env` global da raiz
- `MCP_SERVER_PATH` / `MCP_SERVER_NAME` → se o agente usar MCP, configure via código ou adicione aqui apenas se for específico deste agente
- `AGENT_SYSTEM_PROMPT` → o prompt vive em `prompts/system_prompt.py`
- Variáveis de LLM → ficam no `.env` global ou são hardcoded no `model.py`

### .env global (raiz do projeto)
O arquivo `.env` na raiz contém apenas infra compartilhada:
```env
LOG_LEVEL=INFO
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=CHANGE_ME
REDIS_HOST=redis
REDIS_PORT=6379
```

## Docker Compose

Adicione o serviço em `composes/compose.services.yaml`:

```yaml
agent-<nome>:
  build:
    context: ..
    dockerfile: services/jobs/py-agent-job/Dockerfile
  container_name: agent-<nome>
  restart: unless-stopped
  # Infra compartilhada (.env raiz) + config específica (.env.<nome>)
  env_file:
    - ../.env
    - ../services/jobs/py-agent-job/.env.<nome>
  depends_on:
    rabbitmq:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - agent_platform_network
```

**Pontos-chave:**
- `build.context` é sempre `..` (raiz do repo) porque o Dockerfile copia pacotes compartilhados
- `dockerfile` aponta para o mesmo Dockerfile do `py-agent-job` (imagem única, múltiplos serviços)
- `env_file` lista **dois** arquivos: o global primeiro, o específico depois (o específico sobrescreve se houver conflito)
- `depends_on` garante que RabbitMQ e Redis estejam saudáveis antes de iniciar

## Checklist Pós-Criação

1. ✅ Pasta criada em `src/agents/langchain_agents/<nome>/` com todos os arquivos
2. ✅ `__init__.py` criado em cada subpasta (`graph/`, `prompts/`)
3. ✅ Import adicionado em `src/main.py` e entrada no dicionário `AGENTS`
4. ✅ Arquivo `.env.<nome>` criado com AGENT_ID, fila e routing key
5. ✅ Serviço adicionado em `composes/compose.services.yaml` com env_file duplo
6. ✅ Validação: `uv run python -c "from agents.langchain_agents.<nome>.graph import graph; print('OK')"`
7. ✅ Commit e push das alterações

## Exemplo Completo: Criando "customer-support-agent"

1. Criar pasta: `src/agents/langchain_agents/customer_support_agent/`
2. Criar arquivos modelo (substituindo `<nome>` por `customer_support_agent`)
3. Adicionar em `main.py`:
   ```python
   from agents.langchain_agents.customer_support_agent.graph import graph as cs_graph
   AGENTS = { ..., "customer-support-agent": cs_graph }
   ```
4. Criar `.env.customer-support`:
   ```env
   AGENT_ID=customer-support-agent
   RABBITMQ_QUEUE=agent.customer-support.requests
   RABBITMQ_ROUTING_KEY=agent.customer-support
   ```
5. Adicionar serviço no compose:
   ```yaml
   agent-customer-support:
     build: { context: .., dockerfile: services/jobs/py-agent-job/Dockerfile }
     container_name: agent-customer-support
     env_file: [../.env, ../services/jobs/py-agent-job/.env.customer-support]
     ...
   ```
6. Validar e commitar.