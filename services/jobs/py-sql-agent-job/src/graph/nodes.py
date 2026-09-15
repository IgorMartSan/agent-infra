import os
from functools import lru_cache

from langchain.agents import create_agent

from graph.state import AgentState
from model import get_chat_model
from prompts.system_prompt import SYSTEM_PROMPT
from tools import SQL_TOOLS


@lru_cache(maxsize=1)
def get_sql_agent():
    return create_agent(
        model=get_chat_model(),
        tools=SQL_TOOLS,
        system_prompt=SYSTEM_PROMPT.strip(),
    )


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block if isinstance(block, str) else str(block.get("text", ""))
            for block in content
            if isinstance(block, str) or (isinstance(block, dict) and block.get("type") == "text")
        )
    raise TypeError("O agente SQL retornou conteúdo em formato inválido.")


def receive_message(state: AgentState) -> dict:
    result = get_sql_agent().invoke(
        {"messages": [{"role": "user", "content": state["message"]}]},
        config={"recursion_limit": int(os.getenv("SQL_AGENT_RECURSION_LIMIT", "12"))},
    )
    response = _message_text(result["messages"][-1].content)

    if not response.strip():
        raise RuntimeError("O agente SQL retornou uma resposta vazia.")

    return {"response": response.strip()}
