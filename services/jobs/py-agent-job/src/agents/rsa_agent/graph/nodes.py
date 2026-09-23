"""Nós específicos do agente RSA.

Usa MCP apenas para tools, mas o prompt e a lógica de estado
vivem dentro desta pasta agents/rsa-agent/.
"""
import logging
import os
from uuid import uuid4

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from agents.rsa_agent.graph.state import AgentState
from agents.rsa_agent.prompts.system_prompt import SYSTEM_PROMPT
from agents.rsa_agent.model import get_chat_model

logger = logging.getLogger(__name__)


async def receive_message(state: AgentState) -> dict:
    """Executa a mensagem do usuário no agente RSA com ferramentas MCP."""
    server_path = os.getenv("MCP_SERVER_PATH")
    server_name = os.getenv("MCP_SERVER_NAME", "rsa-db")

    if not server_path:
        raise RuntimeError(
            "MCP_SERVER_PATH não está definido no .env do agente RSA."
        )

    mcp_config = {
        server_name: {
            "command": "python",
            "args": [server_path],
            "transport": "stdio",
        }
    }

    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()

    logger.info(
        "Agente RSA criado com %d tools do MCP server '%s'",
        len(tools),
        server_name,
    )

    agent = create_react_agent(
        model=get_chat_model(),
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    config = {
        "recursion_limit": int(os.getenv("AGENT_RECURSION_LIMIT", "12")),
        "configurable": {"thread_id": state.get("thread_id") or uuid4().hex},
    }

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": state["message"]}]},
        config=config,
    )

    last_message = result["messages"][-1]
    content = getattr(last_message, "content", str(last_message))
    response = content.strip() if isinstance(content, str) else str(content).strip()

    if not response:
        raise RuntimeError("O agente RSA retornou uma resposta vazia.")

    return {"response": response}