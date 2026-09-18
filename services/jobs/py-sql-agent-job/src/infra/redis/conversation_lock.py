from urllib.parse import quote


class ConversationLock:
    """Libera o lock de uma mensagem por conversa, criado pelo gateway.

    O gateway cria a chave chat:lock:{application_id}:{chat_id}:{agent_id}
    com TTL ao aceitar a mensagem. O worker a remove quando publica a
    resposta, liberando a conversa para a próxima mensagem.
    """

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    @staticmethod
    def key_for(application_id: str | None, chat_id: str | None, agent_id: str | None) -> str:
        parts = [application_id or ""]
        if chat_id:
            parts.append(quote(str(chat_id), safe=""))
        if agent_id:
            parts.append(quote(agent_id, safe=""))
        return "chat:lock:" + ":".join(parts)

    def release(self, application_id: str | None, chat_id: str | None, agent_id: str | None) -> None:
        self._redis.delete(self.key_for(application_id, chat_id, agent_id))