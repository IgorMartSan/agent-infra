import json
import logging
import time
import uuid
from typing import Any
from urllib.parse import quote

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class UserMessageBlockedError(Exception):
    """Indica que novas mensagens do usuário foram bloqueadas temporariamente."""

    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        """Inicializa o erro de bloqueio.

        Args:
            message: Motivo legível do bloqueio.
            retry_after_seconds: Tempo mínimo, em segundos, antes de uma nova tentativa.
        """
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ChatMessageGroupRepository:
    """Armazena mensagens e entrega grupos prontos para processamento exclusivo."""

    def __init__(self, redis_connection) -> None:
        """Inicializa o repository com um cliente Redis compartilhado."""
        self.redis: Redis = redis_connection.get_client()
        self.buffer_prefix = "chat:buffer"
        self.index_key = "chat:ready_index:v2"
        self.processing_prefix = "chat:processing"

    def _identity_suffix(self, user_id: str, chat_id: str, agent_id: str) -> str:
        return ":".join(quote(value, safe="") for value in (user_id, chat_id, agent_id))

    def _identity_member(self, user_id: str, chat_id: str, agent_id: str) -> str:
        return json.dumps(
            {"user_id": user_id, "chat_id": chat_id, "agent_id": agent_id},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def _parse_identity_member(self, raw_member: bytes | str) -> dict[str, str] | None:
        normalized = (
            raw_member.decode("utf-8")
            if isinstance(raw_member, bytes)
            else str(raw_member)
        )
        try:
            identity = json.loads(normalized)
        except json.JSONDecodeError:
            return None
        if not isinstance(identity, dict):
            return None

        values = {
            field: str(identity.get(field, "")).strip()
            for field in ("user_id", "chat_id", "agent_id")
        }
        return values if all(values.values()) else None

    def _buffer_key(self, user_id: str, chat_id: str, agent_id: str) -> str:
        suffix = self._identity_suffix(user_id, chat_id, agent_id)
        return f"{self.buffer_prefix}:{suffix}"

    def _lock_key(self, user_id: str, chat_id: str, agent_id: str) -> str:
        suffix = self._identity_suffix(user_id, chat_id, agent_id)
        return f"{self.processing_prefix}:{suffix}"

    def _serialize_payload(self, payload: dict[str, Any] | str) -> str:
        if isinstance(payload, str):
            payload = {"message": payload}
        return json.dumps(payload, ensure_ascii=False)

    def _deserialize_payload(self, raw_message: bytes | str) -> dict[str, Any]:
        normalized = (
            raw_message.decode("utf-8")
            if isinstance(raw_message, bytes)
            else str(raw_message)
        )
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            return {"message": normalized}
        if not isinstance(parsed, dict):
            return {"message": str(parsed)}
        return parsed

    async def add_message(
        self,
        user_id: str,
        payload: dict[str, Any] | str,
        *,
        chat_id: str,
        agent_id: str,
        max_pending_messages: int = 10,
        rate_limit_messages: int = 20,
        rate_limit_window_seconds: int = 60,
        block_seconds: int = 60,
    ) -> None:
        """Adiciona uma mensagem a um buffer isolado por usuário, chat e agente.

        Args:
            user_id: Identificador do usuário dono da mensagem e do buffer.
            chat_id: Identificador da conversa à qual a mensagem pertence.
            agent_id: Nome do agente responsável por processar a mensagem.
            payload: Texto ou dicionário serializável em JSON que será armazenado.
            max_pending_messages: Quantidade máxima de mensagens ainda não
                confirmadas que o usuário pode manter no buffer.
            rate_limit_messages: Quantidade máxima de mensagens aceitas dentro
                da janela de frequência.
            rate_limit_window_seconds: Duração, em segundos, da janela usada
                para contabilizar a frequência de envio.
            block_seconds: Duração, em segundos, do bloqueio aplicado quando
                algum limite é excedido.

        Raises:
            ValueError: Se algum limite configurado for menor ou igual a zero.
            UserMessageBlockedError: Se o usuário estiver bloqueado ou exceder
                o limite de frequência ou de mensagens pendentes.
            RedisError: Se o Redis falhar ao verificar ou armazenar a mensagem.
        """
        if min(
            max_pending_messages,
            rate_limit_messages,
            rate_limit_window_seconds,
            block_seconds,
        ) <= 0:
            raise ValueError("Os limites de mensagens devem ser maiores que zero")

        user_id = str(user_id).strip()
        chat_id = str(chat_id).strip()
        agent_id = str(agent_id).strip().lower()
        if not user_id or not chat_id or not agent_id:
            raise ValueError("user_id, chat_id e agent_id são obrigatórios")

        now = time.time()
        identity_member = self._identity_member(user_id, chat_id, agent_id)
        script = """
        local block_key = KEYS[1]
        local rate_key = KEYS[2]
        local buffer_key = KEYS[3]
        local index_key = KEYS[4]

        local identity_member = ARGV[1]
        local payload = ARGV[2]
        local now = tonumber(ARGV[3])
        local request_id = ARGV[4]
        local max_pending = tonumber(ARGV[5])
        local rate_limit = tonumber(ARGV[6])
        local rate_window = tonumber(ARGV[7])
        local block_seconds = tonumber(ARGV[8])

        if redis.call("EXISTS", block_key) == 1 then
            return {0, redis.call("TTL", block_key)}
        end

        redis.call("ZREMRANGEBYSCORE", rate_key, 0, now - rate_window)

        if redis.call("ZCARD", rate_key) >= rate_limit then
            redis.call("SET", block_key, "rate_limit", "EX", block_seconds)
            redis.call("DEL", rate_key)
            return {-1, block_seconds}
        end

        if redis.call("LLEN", buffer_key) >= max_pending then
            redis.call("SET", block_key, "pending_limit", "EX", block_seconds)
            return {-2, block_seconds}
        end

        redis.call("ZADD", rate_key, now, request_id)
        redis.call("EXPIRE", rate_key, rate_window)
        redis.call("RPUSH", buffer_key, payload)
        redis.call("ZADD", index_key, now, identity_member)
        return {1, 0}
        """

        try:
            result = await self.redis.eval(
                script,
                4,
                f"chat:block:{quote(user_id, safe='')}",
                f"chat:rate:{quote(user_id, safe='')}",
                self._buffer_key(user_id, chat_id, agent_id),
                self.index_key,
                identity_member,
                self._serialize_payload(payload),
                str(now),
                str(uuid.uuid4()),
                str(max_pending_messages),
                str(rate_limit_messages),
                str(rate_limit_window_seconds),
                str(block_seconds),
            )
        except RedisError:
            logger.exception("Erro ao adicionar mensagem no Redis")
            raise

        status = int(result[0])
        retry_after = max(1, int(result[1]))
        if status == 1:
            return
        if status == -1:
            message = "Frequência de mensagens excedida; usuário bloqueado temporariamente."
        elif status == -2:
            message = "Limite de mensagens pendentes excedido; usuário bloqueado temporariamente."
        else:
            message = "Usuário temporariamente bloqueado para novas mensagens."

        raise UserMessageBlockedError(message, retry_after_seconds=retry_after)

    async def claim_ready_message_group(
        self,
        *,
        idle_seconds: float = 1,
        candidate_limit: int = 100,
        max_messages: int = 100,
        lock_ttl_seconds: int = 30,
    ) -> dict[str, Any] | None:
        """Reserva um grupo pronto ou devolve ``None`` quando não há trabalho.

        Args:
            idle_seconds: Tempo mínimo, em segundos, sem novas mensagens para
                considerar o grupo pronto para processamento.
            candidate_limit: Quantidade máxima de usuários prontos examinados
                nesta tentativa. Candidatos já bloqueados são ignorados.
            max_messages: Quantidade máxima de mensagens devolvidas no grupo.
                Mensagens excedentes permanecem no buffer para o próximo grupo.
            lock_ttl_seconds: Prazo, em segundos, para o lock expirar
                automaticamente caso o worker não confirme nem libere o grupo.

        Returns:
            Um dicionário com ``user_id``, ``messages``, ``message_count``,
            ``full_text`` e ``lock_token``; ou ``None`` se nenhum grupo puder
            ser reservado.

        Raises:
            RedisError: Se o Redis falhar durante a busca ou aquisição do lock.
        """
        try:
            cutoff = time.time() - idle_seconds
            identities = await self.redis.zrangebyscore(
                self.index_key,
                min=0,
                max=cutoff,
                start=0,
                num=candidate_limit,
            )

            for raw_identity in identities:
                identity = self._parse_identity_member(raw_identity)
                if identity is None:
                    await self.redis.zrem(self.index_key, raw_identity)
                    continue
                message_group = await self._collect_user_messages(
                    **identity,
                    max_messages=max_messages,
                    lock_ttl_seconds=lock_ttl_seconds,
                )
                if message_group is not None:
                    return message_group

            return None
        except RedisError:
            logger.exception("Erro ao reservar grupo de mensagens no Redis")
            raise

    async def ack_message_group(
        self,
        user_id: str,
        chat_id: str,
        agent_id: str,
        lock_token: str,
        message_count: int,
    ) -> bool:
        """Confirma o grupo processado e preserva mensagens posteriores.

        Args:
            user_id: Identificador do usuário dono do grupo.
            chat_id: Identificador do chat dono do grupo.
            agent_id: Nome do agente dono do grupo.
            lock_token: Token recebido ao reservar o grupo, usado para provar
                que este worker ainda é o proprietário do lock.
            message_count: Quantidade de mensagens processadas que deve ser
                removida do início do buffer.

        Returns:
            ``True`` quando o token é válido e a confirmação é concluída;
            ``False`` quando o lock expirou ou pertence a outro worker.

        Raises:
            RedisError: Se o Redis falhar ao confirmar o grupo.
        """
        script = """
        local lock_key = KEYS[1]
        local buffer_key = KEYS[2]
        local index_key = KEYS[3]
        local expected_token = ARGV[1]
        local identity_member = ARGV[2]
        local processed_count = tonumber(ARGV[3])

        local current_token = redis.call("GET", lock_key)
        if not current_token or current_token ~= expected_token then
            return 0
        end

        redis.call("LTRIM", buffer_key, processed_count, -1)
        if redis.call("LLEN", buffer_key) == 0 then
            redis.call("DEL", buffer_key)
            redis.call("ZREM", index_key, identity_member)
        else
            redis.call("ZADD", index_key, redis.call("TIME")[1], identity_member)
        end
        redis.call("DEL", lock_key)
        return 1
        """
        try:
            result = await self.redis.eval(
                script,
                3,
                self._lock_key(user_id, chat_id, agent_id),
                self._buffer_key(user_id, chat_id, agent_id),
                self.index_key,
                lock_token,
                self._identity_member(user_id, chat_id, agent_id),
                str(message_count),
            )
            return result == 1
        except RedisError:
            logger.exception("Erro ao confirmar grupo do user_id=%s", user_id)
            raise

    async def release_message_group(
        self,
        user_id: str,
        chat_id: str,
        agent_id: str,
        lock_token: str,
    ) -> bool:
        """Libera o grupo sem remover suas mensagens para permitir nova tentativa.

        Args:
            user_id: Identificador do usuário dono do grupo.
            chat_id: Identificador do chat dono do grupo.
            agent_id: Nome do agente dono do grupo.
            lock_token: Token recebido ao reservar o grupo, usado para impedir
                que um worker libere o lock adquirido por outro.

        Returns:
            ``True`` quando o lock pertence ao token e é liberado; ``False``
            quando o lock não existe mais ou pertence a outro worker.

        Raises:
            RedisError: Se o Redis falhar ao liberar o grupo.
        """
        script = """
        local lock_key = KEYS[1]
        local expected_token = ARGV[1]
        local current_token = redis.call("GET", lock_key)

        if not current_token or current_token ~= expected_token then
            return 0
        end

        redis.call("DEL", lock_key)
        return 1
        """
        try:
            result = await self.redis.eval(
                script,
                1,
                self._lock_key(user_id, chat_id, agent_id),
                lock_token,
            )
            return result == 1
        except RedisError:
            logger.exception("Erro ao liberar grupo do user_id=%s", user_id)
            raise

    async def _collect_user_messages(
        self,
        *,
        user_id: str,
        chat_id: str,
        agent_id: str,
        max_messages: int,
        lock_ttl_seconds: int,
    ) -> dict[str, Any] | None:
        lock_token = str(uuid.uuid4())
        acquired = await self.redis.set(
            self._lock_key(user_id, chat_id, agent_id),
            lock_token,
            nx=True,
            ex=lock_ttl_seconds,
        )
        if not acquired:
            return None

        try:
            raw_messages = await self.redis.lrange(
                self._buffer_key(user_id, chat_id, agent_id),
                0,
                max_messages - 1,
            )
            if not raw_messages:
                identity_member = self._identity_member(user_id, chat_id, agent_id)
                await self.redis.zrem(self.index_key, identity_member)
                await self.release_message_group(
                    user_id, chat_id, agent_id, lock_token
                )
                return None

            messages = [
                self._deserialize_payload(raw_message)
                for raw_message in raw_messages
            ]
            return {
                "user_id": user_id,
                "chat_id": chat_id,
                "agent_id": agent_id,
                "messages": messages,
                "message_count": len(messages),
                "full_text": "\n".join(
                    str(message.get("message", "")) for message in messages
                ),
                "lock_token": lock_token,
            }
        except RedisError:
            logger.exception("Erro ao coletar mensagens do user_id=%s", user_id)
            await self.release_message_group(user_id, chat_id, agent_id, lock_token)
            raise
