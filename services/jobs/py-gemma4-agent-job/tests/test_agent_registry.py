from infra.redis import AgentRegistry, ConversationLock


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    def set(self, key: str, value: str, ex: int) -> None:
        self.values[key] = value
        self.expirations[key] = ex

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


def test_worker_registers_and_removes_heartbeat() -> None:
    redis = FakeRedis()
    registry = AgentRegistry(redis, "gemma4-agent", ttl_seconds=30, interval_seconds=60)

    registry.start()
    assert redis.values["agent:online:gemma4-agent"] == "1"
    assert redis.expirations["agent:online:gemma4-agent"] == 30

    registry.stop()
    assert "agent:online:gemma4-agent" not in redis.values


def test_completed_message_releases_gateway_lock() -> None:
    redis = FakeRedis()
    key = "chat:lock:chatbot-next:chat%2F1:gemma4-agent"
    redis.values[key] = "1"

    ConversationLock(redis).release("chatbot-next", "chat/1", "gemma4-agent")

    assert key not in redis.values
