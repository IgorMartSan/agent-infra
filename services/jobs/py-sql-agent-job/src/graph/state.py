from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    message: str
    response: str
    thread_id: NotRequired[str]
