from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    """Estado específico do agente RSA."""
    message: str
    response: str
    thread_id: NotRequired[str]