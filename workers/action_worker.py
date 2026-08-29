import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Bot

from queues.actions import get_action, close_action_queue
from services.telegram_actions import execute_mute


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is missing from .env"
    )


async def process_action(bot: Bot, action: dict):
    action_type = action.get("action")

    chat_id = int(action["chat_id"])
    user_id = int(action["user_id"])
    message_id = int(action["message_id"])

    reason = action.get(
        "reason",
        "Moderation violation",
    )

    logger.info(
        "Processing action=%s chat=%s user=%s message=%s",
        action_type,
        chat_id,
        user_id,
        message_id,
    )

    if action_type == "mute":
        result = await execute_mute(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            message_id=message_id,
            reason=reason,
        )

        logger.info(
            "Moderation result: %s",
            result,
        )

        return

    logger.warning(
        "Unknown moderation action: %s",
        action_type,
    )


async def main():
    bot = Bot(token=BOT_TOKEN)

    logger.info(
        "⚡ Action worker started"
    )

    try:
        while True:
            action = await get_action(
                timeout=5
            )

            if action is None:
                await asyncio.sleep(0.05)
                continue

            try:
                await process_action(
                    bot,
                    action,
                )

            except Exception:
                logger.exception(
                    "Failed to process moderation action"
                )

    except asyncio.CancelledError:
        raise

    finally:
        await bot.shutdown()
        await close_action_queue()

        logger.info(
            "Action worker stopped"
        )


if __name__ == "__main__":
    asyncio.run(main())
