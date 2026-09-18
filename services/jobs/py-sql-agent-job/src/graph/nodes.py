import logging
import os
from functools import lru_cache
from uuid import uuid4

from langchain.agents import create_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from graph.memory import checkpoint_messages, replace_messages, trim_history
from graph.state import AgentState
from infra.sql_database import get_database_engine
from model import get_chat_model
from prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def build_sql_agent():
    """Cria o agente SQL com as ferramentas do SQLDatabaseToolkit da comunidade."""
    database = SQLDatabase(engine=get_database_engine(), sample_rows_in_table_info=0)
    toolkit = SQLDatabaseToolkit(db=database, llm=get_chat_model())
    return create_agent(
        model=get_chat_model(),
        tools=toolkit.get_tools(),
        system_prompt=SYSTEM_PROMPT.strip(),
        checkpointer=InMemorySaver(),
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


def _answer_from_tool_results(messages: list, question: str) -> str:
    """Pede a resposta final sem ferramentas quando o modelo encerra vazio."""
    tool_messages = [message for message in messages if getattr(message, "type", None) == "tool"]
    if not tool_messages:
        return ""

    results = []
    for message in tool_messages[-2:]:
        content = _message_text(message.content)
        if len(content) > 2500:
            content = content[:2500] + "\n[resultado truncado]"
        results.append(f"{getattr(message, 'name', 'ferramenta')}: {content}")

    answer = get_chat_model().invoke(
        [
            (
                "system",
                "Responda em português usando apenas os resultados das ferramentas. "
                + "Se forem insuficientes, explique o que falta. Não execute consultas.",
            ),
            ("human", f"Pergunta: {question}\n\nResultados:\n" + "\n\n".join(results)),
        ]
    )
    return _message_text(answer.content).strip()


def receive_message(state: AgentState) -> dict:
    agent = build_sql_agent()
    config = {
        "recursion_limit": int(os.getenv("SQL_AGENT_RECURSION_LIMIT", "12")),
        "configurable": {"thread_id": state.get("thread_id") or uuid4().hex},
    }
    previous_messages = checkpoint_messages(agent, config)

    try:
        for attempt in range(2):
            result = agent.invoke(
                {"messages": [{"role": "user", "content": state["message"]}]},
                config=config,
            )
            last_message = result["messages"][-1]
            response = _message_text(last_message.content).strip()
            if response:
                trim_history(agent, config)
                return {"response": response}

            metadata = getattr(last_message, "response_metadata", {})
            logger.warning(
                "Resposta vazia do modelo SQL: tentativa=%s finish_reason=%s tool_calls=%s completion_tokens=%s",
                attempt + 1,
                metadata.get("finish_reason"),
                len(getattr(last_message, "tool_calls", [])),
                (metadata.get("token_usage") or {}).get("completion_tokens"),
            )

            fallback = _answer_from_tool_results(result["messages"], state["message"])
            if fallback:
                agent.update_state(
                    config,
                    {"messages": [AIMessage(id=last_message.id, content=fallback)]},
                )
                trim_history(agent, config)
                return {"response": fallback}

            replace_messages(agent, config, previous_messages)
    except Exception:
        replace_messages(agent, config, previous_messages)
        raise

    raise RuntimeError("O agente SQL retornou uma resposta vazia em duas tentativas.")
