import pytest
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from graph import nodes
from graph.memory import checkpoint_messages, thread_id_for, trim_history


def test_thread_id_is_stable_and_isolated() -> None:
    payload = {
        "application_id": "app",
        "user_id": "user-1",
        "chat_id": "chat-1",
        "agent_id": "sql-agent",
    }

    assert thread_id_for(payload) == thread_id_for(payload)
    assert thread_id_for(payload) != thread_id_for({**payload, "user_id": "user-2"})
    assert thread_id_for(payload) != thread_id_for({**payload, "chat_id": "chat-2"})
    assert thread_id_for(payload) != thread_id_for({**payload, "agent_id": "other-agent"})
    assert thread_id_for({**payload, "chat_id": None}) != thread_id_for({**payload, "chat_id": None})


def test_in_memory_checkpoint_retains_at_most_60_messages_per_thread() -> None:
    model = GenericFakeChatModel(messages=iter(f"answer-{index}" for index in range(33)))
    agent = create_agent(model=model, tools=[], checkpointer=InMemorySaver())
    first_thread = {"configurable": {"thread_id": "conversation-1"}}
    second_thread = {"configurable": {"thread_id": "conversation-2"}}

    for index in range(32):
        agent.invoke({"messages": [{"role": "user", "content": f"question-{index}"}]}, first_thread)
        trim_history(agent, first_thread)

    messages = checkpoint_messages(agent, first_thread)
    assert len(messages) == 60
    assert messages[0].type == "human"
    assert messages[0].content == "question-2"
    assert messages[-1].content == "answer-31"

    agent.invoke({"messages": [{"role": "user", "content": "other question"}]}, second_thread)
    assert len(checkpoint_messages(agent, second_thread)) == 2
    assert len(checkpoint_messages(agent, first_thread)) == 60


def test_fallback_answer_replaces_empty_final_message_in_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @tool
    def list_tables() -> str:
        """List available tables."""
        return "orders, users"

    class ToolCallingFakeModel(GenericFakeChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    model = ToolCallingFakeModel(
        messages=iter(
            [
                AIMessage(content="", tool_calls=[{"name": "list_tables", "args": {}, "id": "call-1"}]),
                AIMessage(content=""),
            ]
        )
    )
    agent = create_agent(model=model, tools=[list_tables], checkpointer=InMemorySaver())

    class FinalModel:
        def invoke(self, messages: list) -> AIMessage:
            return AIMessage(content="Tabelas: orders e users.")

    monkeypatch.setattr(nodes, "build_sql_agent", lambda: agent)
    monkeypatch.setattr(nodes, "get_chat_model", FinalModel)

    assert nodes.receive_message({"message": "Quais as tabelas?", "response": "", "thread_id": "fallback-thread"}) == {
        "response": "Tabelas: orders e users."
    }

    messages = checkpoint_messages(agent, {"configurable": {"thread_id": "fallback-thread"}})
    assert [message.type for message in messages] == ["human", "ai"]
    assert messages[-1].content == "Tabelas: orders e users."


def test_failed_response_does_not_duplicate_question_in_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = GenericFakeChatModel(messages=iter(["first answer", "", ""]))
    agent = create_agent(model=model, tools=[], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "retry-thread"}}
    agent.invoke({"messages": [{"role": "user", "content": "first question"}]}, config)
    monkeypatch.setattr(nodes, "build_sql_agent", lambda: agent)

    with pytest.raises(RuntimeError, match="resposta vazia"):
        nodes.receive_message({"message": "second question", "response": "", "thread_id": "retry-thread"})

    assert [message.content for message in checkpoint_messages(agent, config)] == [
        "first question",
        "first answer",
    ]
