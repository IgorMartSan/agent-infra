import unittest

from exemples import DEFAULT_AGENT, SIMPLE_AGENT, SimpleAgent, TestAgent, get_agent


class TestAgentTest(unittest.TestCase):
    def test_has_a_string_name(self) -> None:
        self.assertIsInstance(DEFAULT_AGENT.name, str)
        self.assertEqual(DEFAULT_AGENT.name, "agent1")

    def test_concatenates_received_messages(self) -> None:
        agent = TestAgent()

        response = agent.respond(
            "chat-1",
            [
                {"message": "primeira"},
                {"message": "segunda"},
                {"message": "terceira"},
            ],
        )

        self.assertEqual(
            response,
            "Oi, sou o agente 1. As suas mensagens foram: primeira | segunda | terceira",
        )

    def test_uses_default_agent_when_name_is_missing(self) -> None:
        self.assertIs(get_agent(None), DEFAULT_AGENT)
        self.assertIs(get_agent(""), DEFAULT_AGENT)

    def test_uses_default_agent_when_name_is_unknown(self) -> None:
        self.assertIs(get_agent("unknown-agent"), DEFAULT_AGENT)

    def test_selects_registered_agent_by_normalized_name(self) -> None:
        self.assertIs(get_agent(" AGENT1 "), DEFAULT_AGENT)

    def test_selects_simple_langgraph_agent(self) -> None:
        self.assertIs(get_agent(" AGENT2 "), SIMPLE_AGENT)

    def test_simple_agent_concatenates_messages_without_llm(self) -> None:
        agent = SimpleAgent()

        response = agent.respond(
            "chat-1",
            [
                {"message": "primeira"},
                {"message": "segunda"},
            ],
        )

        self.assertEqual(
            response,
            "Oi, sou o agente 2. As suas mensagens foram: primeira | segunda",
        )


if __name__ == "__main__":
    unittest.main()
