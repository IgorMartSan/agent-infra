"""Nó do grafo que executa o agente RSA com ferramentas MCP."""

import logging
import os
from functools import lru_cache
from uuid import uuid4

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from graph.state import AgentState
from model import get_chat_model
from prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_mcp_server_path() -> str:
    return os.getenv("MCP_SERVER_PATH", "../../mcps/py-mcp-infra-test/src/main.py")


async def _build_agent():
    """Cria o agente ReAct conectado ao servidor MCP via stdio."""
    server_path = _get_mcp_server_path()
    client = MultiServerMCPClient(
        {
            "rsa-db": {
                "command": "python",
                "args": [server_path],
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()
    return create_react_agent(
        model=get_chat_model(),
        tools=tools,
        prompt=SYSTEM_PROMPT.strip(),
    )


async def receive_message(state: AgentState) -> dict:
    """Executa a mensagem do usuário no agente RSA com ferramentas MCP."""
    agent = await _build_agent()
    config = {
        "recursion_limit": int(os.getenv("RSA_AGENT_RECURSION_LIMIT", "12")),
        "configurable": {"thread_id": state.get("thread_id") or uuid4().hex},
    }

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": state["message"]}]},
        config=config,
    )

    last_message = result["messages"][-1]
    content = last_message.content if hasattr(last_message, "content") else str(last_message)
    response = content.strip() if isinstance(content, str) else str(content).strip()

    if not response:
        raise RuntimeError("O agente RSA retornou uma resposta vazia.")

    return {"response": response}