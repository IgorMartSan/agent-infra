from langgraph.graph import StateGraph, START, END

from .state import AgentState
from .nodes import receive_message


builder = StateGraph(AgentState)

builder.add_node(
    "receive_message",
    receive_message,
)

builder.add_edge(
    START,
    "receive_message",
)

builder.add_edge(
    "receive_message",
    END,
)

graph = builder.compile()
