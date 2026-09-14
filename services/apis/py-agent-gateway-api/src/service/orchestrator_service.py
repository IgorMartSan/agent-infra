class OrchestratorService:

    def __init__(self, agents):
        self._agents = agents

    def process(self, message: dict) -> str:
        agent_id = message['agent_id']

        agent = self._agents[agent_id]

        return agent.execute(message)
