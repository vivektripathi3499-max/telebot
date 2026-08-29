import time

from queues.redis_queue import RedisQueue


ACTION_QUEUE = "moderation:actions"

_action_queue = RedisQueue(ACTION_QUEUE)


async def queue_action(
    chat_id: int,
    user_id: int,
    message_id: int,
    action: str,
    reason: str,
    severity: int = 50,
) -> None:
    """
    Put a moderation action into Redis.

    The Telegram API is deliberately NOT called here.
    A dedicated action worker will execute it.
    """

    await _action_queue.put(
        {
            "chat_id": chat_id,
            "user_id": user_id,
            "message_id": message_id,
            "action": action,
            "reason": reason,
            "severity": severity,
            "created_at": time.time(),
        }
    )


async def get_action(timeout: int = 5):
    """Retrieve the next moderation action."""

    return await _action_queue.get(timeout=timeout)


async def close_action_queue() -> None:
    await _action_queue.close()

