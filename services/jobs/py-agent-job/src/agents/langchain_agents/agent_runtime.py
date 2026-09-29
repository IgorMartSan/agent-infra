"""Interface ?nica entre o worker e os grafos dos agentes."""

import asyncio
import os
from contextlib import AsyncExitStack, contextmanager
from importlib import import_module
from uuid import uuid4

from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.postgres.shallow import AsyncShallowPostgresSaver

from agents.catalog import AgentProcessingError
from entity.message import AgentMessage

AGENTS = {
    "simple-agent": "agents.langchain_agents.simple_agent.graph",
    "rsa-agent": "agents.langchain_agents.rsa_flow.graph",
    "argus-agent": "agents.langchain_agents.argus_agent.graph.graph",
}


class AgentRuntime:
    def __init__(self, agent_id: str, module, runner: asyncio.Runner) -> None:
        self.agent_id = agent_id
        self.module = module
        self.runner = runner
        self.resources = AsyncExitStack()
        self.graph = None

    async def start(self) -> None:
        if self.agent_id == "rsa-agent":
            checkpointer = await self.resources.enter_async_context(
                AsyncShallowPostgresSaver.from_conn_string(os.environ["RSA_CHECKPOINT_DATABASE_URL"])
            )
            await checkpointer.setup()
            self.graph = self.module.build_graph(checkpointer)
        elif hasattr(self.module, "build_graph"):
            self.graph = self.module.build_graph()
        else:
            self.graph = self.module.graph

    def invoke(self, message: AgentMessage) -> str:
        try:
            conversation_id = message.chat_id or uuid4().hex
            langfuse_handler = CallbackHandler()
            config = {
                "callbacks": [langfuse_handler],
                "configurable": {"thread_id": conversation_id},
                "metadata": {"langfuse_session_id": conversation_id, "langfuse_tags": [self.agent_id]},
            }
            if hasattr(self.module, "invoke"):
                response = self.runner.run(self.module.invoke(self.graph, message, config))
            else:
                state = {"message": message.message, "response": "", "thread_id": conversation_id}
                result = self.runner.run(self.graph.ainvoke(state, config=config))
                response = result.get("response")
            if not isinstance(response, str) or not response.strip():
                raise ValueError("O agente retornou uma resposta vazia.")
            return response
        except Exception as error:
            raise AgentProcessingError("Não foi possível processar a mensagem. Tente novamente.") from error

    async def stop(self) -> None:
        await self.resources.aclose()


@contextmanager
def get_agent(agent_id: str):
    try:
        module_path = AGENTS[agent_id]
    except KeyError as error:
        raise ValueError(f"Agente '{agent_id}' desconhecido.") from error

    module = import_module(module_path)
    with asyncio.Runner() as runner:
        agent = AgentRuntime(agent_id, module, runner)
        try:
            runner.run(agent.start())
            yield agent
        finally:
            runner.run(agent.stop())
