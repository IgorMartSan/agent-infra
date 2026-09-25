from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class AgentState(TypedDict):
    message: str
    response: str


SYSTEM_PROMPT = """Eu sou o Simple Agent.

Sou um agente simples criado para testar o funcionamento do LangGraph.
Minha função atual é receber uma mensagem do usuário e retornar essa mesma
mensagem informando que ela foi recebida."""


def receive_message(state: AgentState) -> dict[str, str]:
    return {"response": f"{SYSTEM_PROMPT}\n\nEu recebi a mensagem: {state['message']}"}


builder = StateGraph(AgentState)
builder.add_node("receive_message", receive_message)
builder.add_edge(START, "receive_message")
builder.add_edge("receive_message", END)

graph = builder.compile()
