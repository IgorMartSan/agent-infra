from urllib.parse import quote


class ConversationLockUnavailable(Exception):
    """Indica que a conversa já possui uma mensagem em processamento."""


class ConversationLock:
    """Garante no máximo uma mensagem em processamento por conversa.

    A chave é a combinação de application_id, chat_id e agent_id.
    O lock é criado com TTL: se o worker cair sem liberar, a chave
    expira sozinha e a conversa volta a aceitar mensagens.
    """

    def __init__(self, redis_client, ttl_seconds: int = 300) -> None:
        self._redis = redis_client
        self._ttl = ttl_seconds

    @staticmethod
    def key_for(application_id: str, chat_id: str | None, agent_id: str) -> str:
        parts = [application_id]
        if chat_id:
            parts.append(quote(str(chat_id), safe=''))
        parts.append(quote(agent_id, safe=''))
        return 'chat:lock:' + ':'.join(parts)

    def acquire(self, application_id: str, chat_id: str | None, agent_id: str) -> None:
        key = self.key_for(application_id, chat_id, agent_id)
        if not self._redis.set(key, '1', nx=True, ex=self._ttl):
            raise ConversationLockUnavailable(
                'Já existe uma mensagem em processamento para esta conversa. '
                'Aguarde a resposta anterior antes de enviar uma nova mensagem.'
            )

    def release(self, application_id: str, chat_id: str | None, agent_id: str) -> None:
        key = self.key_for(application_id, chat_id, agent_id)
        self._redis.delete(key)
