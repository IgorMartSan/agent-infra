from langgraph.graph import END, START, StateGraph

from agents.langchain_agents.rsa_agent.graph.nodes import receive_message
from agents.langchain_agents.rsa_agent.graph.state import AgentState

builder = StateGraph(AgentState)
builder.add_node("receive_message", receive_message)
builder.add_edge(START, "receive_message")
builder.add_edge("receive_message", END)

graph = builder.compile()