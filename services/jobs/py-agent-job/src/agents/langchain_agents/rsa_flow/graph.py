import os
from typing import Annotated, Literal, NotRequired

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from entity.message import AgentMessage

from .nodes import chat_node, summarize_node


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    summary: NotRequired[str]
    response: NotRequired[str]


def should_summarize(state: AgentState) -> Literal["summarize", "__end__"]:
    max_messages = int(os.environ["RSA_MEMORY_MAX_MESSAGES"])

    if len(state["messages"]) > max_messages:
        return "summarize"

    return END


def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("chat", chat_node)

    builder.add_node("summarize", summarize_node)

    builder.add_edge(START, "chat")

    builder.add_conditional_edges("chat", should_summarize)

    builder.add_edge("summarize", END)

    return builder.compile(checkpointer=checkpointer)


async def invoke(graph, message: AgentMessage, thread_id: str) -> str:
    state: AgentState = {"messages": [HumanMessage(content=message.message)]}

    result = await graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}})

    response = result.get("response")

    if not isinstance(response, str) or not response.strip():
        raise ValueError("O agente RSA retornou uma resposta vazia.")

    return response
