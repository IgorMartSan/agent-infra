from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class SimpleAgentState(TypedDict):
    """Estado que percorre o grafo do agente."""

    chat_id: str
    messages: list[dict[str, Any]]
    response: str


def build_response(state: SimpleAgentState) -> dict[str, str]:
    """Concatena as mensagens recebidas sem chamar um modelo de linguagem."""
    received_messages = [
        str(message.get("message", "")).strip()
        for message in state["messages"]
        if str(message.get("message", "")).strip()
    ]
    if not received_messages:
        return {"response": "Oi, sou o agente 2. Nenhuma mensagem foi recebida."}

    concatenated_messages = " | ".join(received_messages)
    return {"response": (f"Oi, sou o agente 2. As suas mensagens foram: {concatenated_messages}")}


class SimpleAgent:
    """Agente determinístico implementado como um grafo simples do LangGraph."""

    name = "agent2"

    def __init__(self) -> None:
        graph = StateGraph(SimpleAgentState)
        graph.add_node("build_response", build_response)
        graph.add_edge(START, "build_response")
        graph.add_edge("build_response", END)
        self._graph = graph.compile()

    def respond(self, chat_id: str, messages: list[dict[str, Any]]) -> str:
        """Executa o grafo e devolve a resposta produzida por seu único nó."""
        result = self._graph.invoke(
            {
                "chat_id": chat_id,
                "messages": messages,
                "response": "",
            }
        )
        return result["response"]
