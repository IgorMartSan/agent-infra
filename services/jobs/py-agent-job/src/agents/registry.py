"""Registry de agentes disponíveis.

Mapeia AGENT_ID (definido no .env do serviço) para o módulo de grafo
correspondente dentro de agents/<agent-id>/graph/.
"""
import importlib
import logging

logger = logging.getLogger(__name__)

# Adicione novos agentes aqui: chave = AGENT_ID, valor = caminho do módulo graph
AGENT_MODULES = {
    "rsa-agent": "agents.rsa_agent.graph",
}


def get_agent_graph(agent_id: str):
    """Retorna o objeto `graph` compilado do agente solicitado."""
    module_path = AGENT_MODULES.get(agent_id)
    if not module_path:
        available = ", ".join(sorted(AGENT_MODULES.keys()))
        raise RuntimeError(
            f"Agente '{agent_id}' não encontrado no registry. "
            f"Disponíveis: {available}"
        )

    try:
        module = importlib.import_module(module_path)
    except ImportError as error:
        raise RuntimeError(
            f"Falha ao importar módulo '{module_path}' do agente '{agent_id}': {error}"
        ) from error

    graph = getattr(module, "graph", None)
    if graph is None:
        raise RuntimeError(
            f"Módulo '{module_path}' não exporta um objeto 'graph'."
        )

    logger.info("Agente carregado: agent_id=%s module=%s", agent_id, module_path)
    return graph