from graph.state import AgentState
from prompts.system_prompt import SYSTEM_PROMPT


def receive_message(state: AgentState) -> dict:
    message = state["message"]

    response = f"{SYSTEM_PROMPT.strip()}\n\nEu recebi a mensagem: {message}"

    return {"response": response}
