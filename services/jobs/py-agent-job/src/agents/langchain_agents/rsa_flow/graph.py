import os
from typing import Annotated, Literal, NotRequired

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from entity.message import AgentMessage

from .nodes import chat_node, summarize_node
from .planner import planner_node
from .validation import prepare_turn, validate_response_node


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    summary: NotRequired[str]
    response: NotRequired[str]
    candidate_response: NotRequired[str]
    attempt_messages: NotRequired[list[AnyMessage]]
    tool_results: NotRequired[list[dict]]
    tools_inventory: NotRequired[str]
    catalog_complete: NotRequired[bool]
    retry_count: NotRequired[int]
    retry_feedback: NotRequired[str]
    retry_response: NotRequired[bool]
    plan: NotRequired[dict]
    planning_error: NotRequired[bool]


def should_summarize(state: AgentState) -> Literal["summarize", "__end__"]:
    max_messages = int(os.environ["RSA_MEMORY_MAX_MESSAGES"])

    if len(state["messages"]) > max_messages:
        return "summarize"

    return END


def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("chat", chat_node)
    builder.add_node("prepare_turn", prepare_turn)
    builder.add_node("validate_response", validate_response_node)
    builder.add_node("planner", planner_node)

    builder.add_node("summarize", summarize_node)

    builder.add_edge(START, "prepare_turn")
    builder.add_edge("prepare_turn", "planner")
    builder.add_edge("planner", "chat")
    builder.add_edge("chat", "validate_response")

    builder.add_conditional_edges("validate_response", route_after_validation)

    builder.add_edge("summarize", END)

    return builder.compile(checkpointer=checkpointer)


def route_after_validation(state: AgentState) -> Literal["planner", "summarize", "__end__"]:
    if state.get("retry_response"):
        return "planner"
    return should_summarize(state)


async def invoke(graph, message: AgentMessage, config: dict) -> str:
    state: AgentState = {"messages": [HumanMessage(content=message.message)]}

    result = await graph.ainvoke(state, config=config)

    response = result.get("response")

    if not isinstance(response, str) or not response.strip():
        raise ValueError("O agente RSA retornou uma resposta vazia.")

    return response
