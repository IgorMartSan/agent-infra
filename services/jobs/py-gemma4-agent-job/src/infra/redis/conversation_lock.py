from urllib.parse import quote


class ConversationLock:
    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    def release(self, application_id: str, chat_id: str | None, agent_id: str) -> None:
        parts = [application_id or ""]
        if chat_id:
            parts.append(quote(chat_id, safe=""))
        parts.append(quote(agent_id, safe=""))
        self._redis.delete("chat:lock:" + ":".join(parts))
