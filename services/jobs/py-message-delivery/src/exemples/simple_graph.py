from typing import Annotated, TypedDict

from config.settings import settings
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    summary: str


def build_llm() -> ChatOllama:
    provider = settings.llm_model_provider
    if provider != "ollama":
        raise ValueError(f"LLM_MODEL_PROVIDER nao suportado: {provider}")

    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.base_url,
        temperature=settings.llm_temperature,
    )


def build_embedding_model() -> OllamaEmbeddings:
    provider = settings.embedding_model_provider
    if provider != "ollama":
        raise ValueError(f"EMBEDDING_MODEL_PROVIDER nao suportado: {provider}")

    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
    )


@tool
def generate_embedding(text: str) -> list[float]:
    """Gera um embedding para uma string usando o modelo configurado."""
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("text nao pode ser vazio")

    return embedding_model.embed_query(normalized_text)


embedding_model = build_embedding_model()
tools = [generate_embedding]

llm = build_llm()
llm_with_tools = llm.bind_tools(tools)


def chatbot_node(state: ChatState):
    summary = state.get("summary", "")

    messages = state["messages"]

    if summary:
        system_message = SystemMessage(content=f"Resumo da conversa anterior:\n{summary}")
        messages = [system_message] + messages

    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


def summarize_node(state: ChatState):
    summary = state.get("summary", "")

    if summary:
        prompt = (
            f"Resumo atual:\n{summary}\n\n"
            "Atualize o resumo com as novas mensagens da conversa. "
            "Mantenha apenas informações importantes, decisões, contexto do usuário e preferências."
        )
    else:
        prompt = (
            "Crie um resumo da conversa. "
            "Mantenha apenas informações importantes, decisões, contexto do usuário e preferências."
        )

    response = llm.invoke(state["messages"] + [HumanMessage(content=prompt)])

    messages_to_delete = [RemoveMessage(id=message.id) for message in state["messages"][:-20]]

    return {
        "summary": response.content,
        "messages": messages_to_delete,
    }


def tool_result_node(state: ChatState):
    tool_message = state["messages"][-1]
    if not isinstance(tool_message, ToolMessage):
        raise TypeError("A ultima mensagem deveria ser o resultado de uma ferramenta")

    return {
        "messages": [
            AIMessage(
                content=(f"Ferramenta {tool_message.name} executada com sucesso.\n\nResultado:\n{tool_message.content}")
            )
        ]
    }


def should_continue_after_chatbot(state: ChatState):
    tool_decision = tools_condition(state)

    if tool_decision == "tools":
        return "tools"

    if len(state["messages"]) > 20:
        return "summarize"

    return END


def build_graph():
    checkpointer = MemorySaver()

    graph = StateGraph(ChatState)

    graph.add_node("chatbot", chatbot_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("tool_result", tool_result_node)
    graph.add_node("summarize", summarize_node)

    graph.add_edge(START, "chatbot")

    graph.add_conditional_edges(
        "chatbot",
        should_continue_after_chatbot,
        {
            "tools": "tools",
            "summarize": "summarize",
            END: END,
        },
    )

    graph.add_edge("tools", "tool_result")
    graph.add_edge("tool_result", END)
    graph.add_edge("summarize", END)

    return graph.compile(checkpointer=checkpointer)


simple_agent = build_graph()
