from langgraph.graph import END, START, StateGraph

from entity.message import AgentMessage

from .nodes import receive_message
from .state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_message", receive_message)
    builder.add_edge(START, "receive_message")
    builder.add_edge("receive_message", END)
    return builder.compile()


async def invoke(graph, message: AgentMessage, config: dict) -> str:
    result = await graph.ainvoke({"message": message.message, "response": ""}, config=config)
    return result["response"]


graph = build_graph()
