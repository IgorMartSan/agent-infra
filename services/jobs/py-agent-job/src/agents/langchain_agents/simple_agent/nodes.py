from .prompts import SYSTEM_PROMPT
from .state import AgentState


def receive_message(state: AgentState) -> dict[str, str]:
    return {"response": f"{SYSTEM_PROMPT}\n\nEu recebi a mensagem: {state['message']}"}
