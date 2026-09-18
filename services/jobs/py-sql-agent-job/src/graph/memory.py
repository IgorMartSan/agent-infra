import hashlib
import json
from collections.abc import Mapping, Sequence
from uuid import uuid4

from langchain_core.messages import BaseMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

MAX_HISTORY_MESSAGES = 60


def thread_id_for(payload: Mapping) -> str:
    """Isola o histórico por aplicação, usuário, conversa e agente."""
    chat_id = payload.get("conversation_id") or payload.get("chat_id")
    if not isinstance(chat_id, str) or not chat_id.strip():
        return uuid4().hex

    identity = [
        payload.get("application_id") or "",
        payload.get("user_id") or "",
        chat_id,
        payload.get("agent_id") or "",
    ]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()


def checkpoint_messages(agent, config: dict) -> list[BaseMessage]:
    return list(agent.get_state(config).values.get("messages", []))


def replace_messages(agent, config: dict, messages: Sequence[BaseMessage]) -> None:
    agent.update_state(
        config,
        {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *messages]},
    )


def trim_history(agent, config: dict) -> None:
    """Guarda até 60 mensagens de conversa, sem os resultados temporários das ferramentas."""
    messages = checkpoint_messages(agent, config)
    conversation = [
        message
        for message in messages
        if message.type == "human" or (message.type == "ai" and not message.tool_calls and message.content)
    ]
    retained = conversation[-MAX_HISTORY_MESSAGES:]
    if retained and retained[0].type != "human":
        retained = retained[1:]

    if [message.id for message in retained] != [message.id for message in messages]:
        replace_messages(agent, config, retained)
