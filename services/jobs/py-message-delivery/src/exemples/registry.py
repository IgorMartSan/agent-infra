from .base import MessageAgent
from .simple_agent import SimpleAgent
from .test_agent import TestAgent

DEFAULT_AGENT = TestAgent()
SIMPLE_AGENT = SimpleAgent()

AGENTS: dict[str, MessageAgent] = {
    DEFAULT_AGENT.name: DEFAULT_AGENT,
    SIMPLE_AGENT.name: SIMPLE_AGENT,
}


def normalize_agent_name(agent_name: str | None) -> str:
    """Normaliza o identificador textual utilizado para selecionar um agente."""
    return agent_name.strip().lower() if agent_name else ""


def get_agent(agent_name: str | None) -> MessageAgent:
    """Retorna o agente solicitado ou o agente padrão quando ele não existir."""
    return AGENTS.get(normalize_agent_name(agent_name), DEFAULT_AGENT)
