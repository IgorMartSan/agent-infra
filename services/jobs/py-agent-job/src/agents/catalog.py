"""Carrega o agente escolhido e expõe uma única chamada: agent.invoke(message)."""

import asyncio
import hashlib
import json
import os
from contextlib import AsyncExitStack, contextmanager
from dataclasses import asdict
from importlib import import_module
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.shallow import AsyncShallowPostgresSaver

from entity.message import AgentMessage

AGENTS = {
    "simple-agent": "agents.langchain_agents.simple_agent.graph",
    "rsa-agent": "agents.langchain_agents.rsa_agent",
    "argus-agent": "agents.langchain_agents.argus_agent.graph.graph",
}


def _thread_id_for(payload: dict) -> str:
    """Isola a memória por aplicação, usuário, conversa e agente."""
    chat_id = payload.get("conversation_id") or payload.get("chat_id")
    if not isinstance(chat_id, str) or not chat_id.strip():
        return uuid4().hex

    identity = [
        payload.get("application_id") or "",
        payload.get("user_id") or "",
        chat_id,
        payload.get("agent_id") or "",
    ]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()


class AgentProcessingError(RuntimeError):
    """Erro do agente que será publicado no chat."""


class Agent:
    def __init__(self, agent_id, graph, runner):
        self.agent_id = agent_id
        self.graph = graph
        self.runner = runner

    def invoke(self, message: AgentMessage) -> str:
        """Converte a mensagem em estado LangGraph e devolve o texto da resposta."""
        thread_id = _thread_id_for(asdict(message))
        state = {"message": message.message, "response": "", "thread_id": thread_id}
        if self.agent_id == "rsa-agent":
            state = {"messages": [HumanMessage(content=message.message)], "response": "", "thread_id": thread_id}
        try:
            result = self.runner.run(self.graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}}))
            response = result.get("response")
            if not isinstance(response, str) or not response.strip():
                raise ValueError("O agente retornou uma resposta vazia.")
            return response
        except Exception as error:
            raise AgentProcessingError("Não foi possível processar a mensagem. Tente novamente.") from error


@contextmanager
def get_agent(agent_id: str):
    """Abre o agente e mantém sua memória disponível enquanto o worker estiver ativo."""
    try:
        module = AGENTS[agent_id]
    except KeyError as error:
        raise ValueError(f"Agente '{agent_id}' desconhecido. Disponíveis: {', '.join(AGENTS)}") from error

    with asyncio.Runner() as runner:
        resources = AsyncExitStack()
        try:
            if agent_id == "rsa-agent":
                checkpointer = runner.run(
                    resources.enter_async_context(
                        AsyncShallowPostgresSaver.from_conn_string(os.environ["RSA_CHECKPOINT_DATABASE_URL"])
                    )
                )
                runner.run(checkpointer.setup())
                graph = import_module(module).build_graph(checkpointer)
            else:
                graph = import_module(module).graph
            yield Agent(agent_id, graph, runner)
        finally:
            runner.run(resources.aclose())
