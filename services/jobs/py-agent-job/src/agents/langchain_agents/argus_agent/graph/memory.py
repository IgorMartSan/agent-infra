from collections.abc import Sequence

from langchain_core.messages import BaseMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

MAX_HISTORY_MESSAGES = 60


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
