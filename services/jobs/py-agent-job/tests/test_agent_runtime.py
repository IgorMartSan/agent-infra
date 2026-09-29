import sys
from importlib import import_module
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.langchain_agents.agent_runtime import AGENTS, get_agent
from entity.message import AgentMessage


def test_registered_agents_load_with_common_runtime():
    for module_path in AGENTS.values():
        import_module(module_path)

    with get_agent("simple-agent") as agent:
        response = agent.invoke(AgentMessage("app", "message", "simple-agent", "olá", "chat", "user"))

    assert "Eu recebi a mensagem: olá" in response
