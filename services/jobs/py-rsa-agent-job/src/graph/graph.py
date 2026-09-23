from langgraph.graph import END, START, StateGraph

from .nodes import receive_message
from .state import AgentState

builder = StateGraph(AgentState)

builder.add_node(
    "receive_message",
    receive_message,
)

builder.add_edge(START, "receive_message")
builder.add_edge("receive_message", END)

graph = builder.compile()