import json

from infra.redis import AgentResponsePubSubRepository


class FakeRedis:
    def __init__(self, subscribers: int = 1) -> None:
        self.subscribers = subscribers
        self.publications: list[tuple[str, str]] = []

    def publish(self, channel: str, message: str) -> int:
        self.publications.append((channel, message))
        return self.subscribers


class FakeRedisConnection:
    def __init__(self, client: FakeRedis) -> None:
        self._client = client

    def get_client(self) -> FakeRedis:
        return self._client


def test_publishes_completed_event_with_received_identifiers() -> None:
    redis = FakeRedis(subscribers=2)
    repository = AgentResponsePubSubRepository(
        FakeRedisConnection(redis),
        channel_prefix="chat:response",
    )

    subscribers = repository.publish_completed(
        application_id="web-chat",
        conversation_id="conv-123",
        message_id="msg-456",
        agent_id="simple-agent",
        content="Eu recebi a mensagem: Olá",
    )

    channel, raw_event = redis.publications[0]
    assert subscribers == 2
    assert channel == "chat:response:web-chat:conv-123"
    assert json.loads(raw_event) == {
        "type": "message.completed",
        "application_id": "web-chat",
        "conversation_id": "conv-123",
        "message_id": "msg-456",
        "agent_id": "simple-agent",
        "content": "Eu recebi a mensagem: Olá",
    }
