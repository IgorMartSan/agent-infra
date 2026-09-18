from infra.redis.agent_registry import AgentRegistry


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.deleted: list[str] = []

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.store.pop(key, None)


def test_start_publishes_heartbeat_key() -> None:
    redis = FakeRedis()
    registry = AgentRegistry(redis, "sql-agent", ttl_seconds=30, interval_seconds=60)

    registry.start()
    # Enquanto o worker vive, a chave de heartbeat existe no Redis.
    assert "agent:online:sql-agent" in redis.store

    registry.stop()
    # No encerramento limpo, o registro é removido.
    assert "agent:online:sql-agent" in redis.deleted
    assert "agent:online:sql-agent" not in redis.store


def test_stop_removes_registration() -> None:
    redis = FakeRedis()
    registry = AgentRegistry(redis, "sql-agent", ttl_seconds=30, interval_seconds=60)

    registry.start()
    assert "agent:online:sql-agent" in redis.store

    registry.stop()
    assert "agent:online:sql-agent" not in redis.store