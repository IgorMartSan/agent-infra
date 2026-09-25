import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.langchain_agents import rsa_agent as agent

pytestmark = pytest.mark.usefixtures("rsa_env")


def test_model_is_new_for_each_message(monkeypatch):
    created = []

    def fake_chat_openai(**kwargs):
        instance = object()
        created.append((instance, kwargs))
        return instance

    monkeypatch.setattr(agent, "ChatOpenAI", fake_chat_openai)

    first = agent.get_chat_model()
    second = agent.get_chat_model()

    assert first is not second
    assert len(created) == 2


def test_missing_model_setting_raises_original_error(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL")

    with pytest.raises(KeyError, match="OPENAI_MODEL"):
        agent.get_chat_model()
