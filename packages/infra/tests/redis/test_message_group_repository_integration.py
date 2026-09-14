import asyncio
import os
import unittest

from infra.redis import (
    ChatMessageGroupRepository,
    RedisConnection,
    UserMessageBlockedError,
)


@unittest.skipUnless(
    os.getenv("RUN_REDIS_INTEGRATION") == "1",
    "Defina RUN_REDIS_INTEGRATION=1 para executar testes contra um Redis real.",
)
class ChatMessageGroupRepositoryIntegrationTest(unittest.IsolatedAsyncioTestCase):
    """Valida scripts Lua, limites e locks usando uma instância real do Redis."""

    async def asyncSetUp(self) -> None:
        test_db = int(os.getenv("TEST_REDIS_DB", "15"))
        if test_db == 0:
            self.fail("TEST_REDIS_DB=0 não é permitido porque os testes executam FLUSHDB")

        self.connection = RedisConnection(
            host=os.getenv("TEST_REDIS_HOST", "localhost"),
            port=int(os.getenv("TEST_REDIS_PORT", "6379")),
            db=test_db,
            password=os.getenv("TEST_REDIS_PASSWORD") or None,
        )
        await self.connection.ping()
        await self.connection.get_client().flushdb()
        self.repository = ChatMessageGroupRepository(self.connection)

    async def asyncTearDown(self) -> None:
        await self.connection.get_client().flushdb()
        await self.connection.close()

    async def test_blocks_eleventh_pending_message(self) -> None:
        for index in range(10):
            await self._add_message(
                f"message-{index}",
                max_pending_messages=10,
                rate_limit_messages=100,
            )

        with self.assertRaises(UserMessageBlockedError) as raised:
            await self._add_message(
                "message-10",
                max_pending_messages=10,
                rate_limit_messages=100,
            )

        self.assertIn("pendentes", str(raised.exception))
        self.assertGreater(raised.exception.retry_after_seconds, 0)
        self.assertEqual(
            await self.connection.get_client().llen(
                "chat:buffer:user-1:chat-1:agent1"
            ),
            10,
        )

    async def test_blocks_when_rate_limit_is_exceeded(self) -> None:
        for index in range(3):
            await self._add_message(
                f"message-{index}",
                max_pending_messages=100,
                rate_limit_messages=3,
            )

        with self.assertRaises(UserMessageBlockedError) as raised:
            await self._add_message(
                "message-3",
                max_pending_messages=100,
                rate_limit_messages=3,
            )

        self.assertIn("Frequência", str(raised.exception))
        self.assertEqual(
            await self.connection.get_client().llen(
                "chat:buffer:user-1:chat-1:agent1"
            ),
            3,
        )

    async def test_concurrent_writes_never_exceed_pending_limit(self) -> None:
        async def send(index: int) -> str:
            try:
                await self._add_message(
                    f"message-{index}",
                    max_pending_messages=10,
                    rate_limit_messages=100,
                )
                return "accepted"
            except UserMessageBlockedError:
                return "blocked"

        results = await asyncio.gather(*(send(index) for index in range(20)))

        self.assertEqual(results.count("accepted"), 10)
        self.assertEqual(results.count("blocked"), 10)
        self.assertEqual(
            await self.connection.get_client().llen(
                "chat:buffer:user-1:chat-1:agent1"
            ),
            10,
        )

    async def test_only_one_worker_claims_message_group(self) -> None:
        await self._add_message("message-1")

        first_group = await self.repository.claim_ready_message_group(idle_seconds=0)
        second_group = await self.repository.claim_ready_message_group(idle_seconds=0)

        self.assertIsNotNone(first_group)
        self.assertIsNone(second_group)

    async def test_expired_lock_allows_another_claim(self) -> None:
        await self._add_message("message-1")

        first_group = await self.repository.claim_ready_message_group(
            idle_seconds=0,
            lock_ttl_seconds=1,
        )
        self.assertIsNotNone(first_group)

        await asyncio.sleep(1.1)

        next_group = await self.repository.claim_ready_message_group(
            idle_seconds=0,
            lock_ttl_seconds=1,
        )
        self.assertIsNotNone(next_group)

    async def test_ack_removes_only_messages_from_claimed_group(self) -> None:
        await self._add_message("message-1")
        await self._add_message("message-2")
        claimed = await self.repository.claim_ready_message_group(idle_seconds=0)
        self.assertIsNotNone(claimed)

        await self._add_message("message-after-claim")

        acknowledged = await self.repository.ack_message_group(
            "user-1",
            "chat-1",
            "agent1",
            str(claimed["lock_token"]),
            int(claimed["message_count"]),
        )

        self.assertTrue(acknowledged)
        remaining = await self.connection.get_client().lrange(
            "chat:buffer:user-1:chat-1:agent1",
            0,
            -1,
        )
        self.assertEqual(len(remaining), 1)
        self.assertIn(b"message-after-claim", remaining[0])

    async def test_release_keeps_messages_available_for_retry(self) -> None:
        await self._add_message("message-1")
        claimed = await self.repository.claim_ready_message_group(idle_seconds=0)
        self.assertIsNotNone(claimed)

        released = await self.repository.release_message_group(
            "user-1",
            "chat-1",
            "agent1",
            str(claimed["lock_token"]),
        )
        claimed_again = await self.repository.claim_ready_message_group(idle_seconds=0)

        self.assertTrue(released)
        self.assertIsNotNone(claimed_again)
        self.assertEqual(claimed_again["messages"], claimed["messages"])

    async def test_ack_with_wrong_token_keeps_messages(self) -> None:
        await self._add_message("message-1")
        claimed = await self.repository.claim_ready_message_group(idle_seconds=0)
        self.assertIsNotNone(claimed)

        acknowledged = await self.repository.ack_message_group(
            "user-1",
            "chat-1",
            "agent1",
            "wrong-token",
            int(claimed["message_count"]),
        )

        self.assertFalse(acknowledged)
        self.assertEqual(
            await self.connection.get_client().llen(
                "chat:buffer:user-1:chat-1:agent1"
            ),
            1,
        )

    async def test_separates_groups_by_user_chat_and_agent(self) -> None:
        await self._add_message("agent-1-chat-1")
        await self._add_message("agent-2-chat-1", agent_id="agent2")
        await self._add_message("agent-1-chat-2", chat_id="chat-2")

        claimed_identities: set[tuple[str, str, str]] = set()
        for _ in range(3):
            claimed = await self.repository.claim_ready_message_group(idle_seconds=0)
            self.assertIsNotNone(claimed)
            identity = (
                str(claimed["user_id"]),
                str(claimed["chat_id"]),
                str(claimed["agent_id"]),
            )
            claimed_identities.add(identity)
            acknowledged = await self.repository.ack_message_group(
                user_id=identity[0],
                chat_id=identity[1],
                agent_id=identity[2],
                lock_token=str(claimed["lock_token"]),
                message_count=int(claimed["message_count"]),
            )
            self.assertTrue(acknowledged)

        self.assertEqual(
            claimed_identities,
            {
                ("user-1", "chat-1", "agent1"),
                ("user-1", "chat-1", "agent2"),
                ("user-1", "chat-2", "agent1"),
            },
        )

    async def _add_message(
        self,
        message: str,
        *,
        chat_id: str = "chat-1",
        agent_id: str = "agent1",
        max_pending_messages: int = 10,
        rate_limit_messages: int = 20,
    ) -> None:
        await self.repository.add_message(
            "user-1",
            {"message": message},
            chat_id=chat_id,
            agent_id=agent_id,
            max_pending_messages=max_pending_messages,
            rate_limit_messages=rate_limit_messages,
            rate_limit_window_seconds=60,
            block_seconds=60,
        )


if __name__ == "__main__":
    unittest.main()
