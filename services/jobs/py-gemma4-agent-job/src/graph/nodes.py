from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState
from model import get_chat_model
from prompts.system_prompt import SYSTEM_PROMPT


def receive_message(state: AgentState) -> dict:
    result = get_chat_model().invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT.strip()),
            HumanMessage(content=state["message"]),
        ]
    )

    if isinstance(result.content, str):
        response = result.content
    elif isinstance(result.content, list):
        response = "\n".join(
            block if isinstance(block, str) else str(block.get("text", ""))
            for block in result.content
            if isinstance(block, str) or block.get("type") == "text"
        )
    else:
        raise TypeError("O modelo Gemma 4 retornou conteúdo em formato inválido.")

    if not response.strip():
        raise RuntimeError("O modelo Gemma 4 retornou uma resposta vazia.")

    return {"response": response.strip()}
