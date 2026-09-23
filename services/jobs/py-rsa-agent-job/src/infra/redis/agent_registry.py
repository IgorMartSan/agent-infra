import logging
import threading

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Mantém o registro de disponibilidade do agente no Redis.

    O worker publica um heartbeat (chave com TTL renovado) enquanto
    está vivo. Se o worker cair, a chave expira e o gateway passa a
    recusar mensagens para este agente.
    """

    def __init__(self, redis_client, agent_id: str, ttl_seconds: int = 30, interval_seconds: float = 10.0) -> None:
        self._redis = redis_client
        self._agent_id = agent_id
        self._ttl = ttl_seconds
        self._interval = interval_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def key(self) -> str:
        return f"agent:online:{self._agent_id}"

    def _heartbeat_once(self) -> None:
        # Renova o TTL: enquanto o worker viver, a chave nunca expira.
        self._redis.set(self.key, "1", ex=self._ttl)

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            try:
                self._heartbeat_once()
            except Exception:
                logger.exception("Falha ao renovar heartbeat do agente %s", self._agent_id)

    def start(self) -> None:
        """Publica o primeiro heartbeat e inicia a renovação em background."""
        self._heartbeat_once()
        self._thread = threading.Thread(
            target=self._run,
            name=f"agent-heartbeat-{self._agent_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Para a renovação e remove o registro (encerramento limpo)."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval)
        try:
            self._redis.delete(self.key)
        except Exception:
            logger.exception("Falha ao remover heartbeat do agente %s", self._agent_id)