import logging
import time

from telegram import ChatPermissions
from telegram.error import TelegramError


logger = logging.getLogger(__name__)


MUTE_SECONDS = 5 * 60


async def delete_message(bot, chat_id: int, message_id: int) -> bool:
    try:
        await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )
        return True

    except TelegramError as exc:
        logger.warning(
            "Unable to delete message %s/%s: %s",
            chat_id,
            message_id,
            exc,
        )
        return False


async def mute_user(bot, chat_id: int, user_id: int) -> bool:
    try:
        until_date = int(time.time()) + MUTE_SECONDS

        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=False,
            ),
            until_date=until_date,
        )

        return True

    except TelegramError as exc:
        logger.warning(
            "Unable to mute user %s in %s: %s",
            user_id,
            chat_id,
            exc,
        )
        return False


async def send_warning(
    bot,
    chat_id: int,
    user_id: int,
    reason: str,
) -> bool:
    try:
        warning = await bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Moderation action\n\n"
                f"User ID: {user_id}\n"
                f"Reason: {reason}\n\n"
                "The user has been muted for 5 minutes."
            ),
        )

        # The worker can later schedule deletion of this warning.
        # Keeping the message ID lets us do that safely.
        return warning.message_id is not None

    except TelegramError as exc:
        logger.warning(
            "Unable to send warning in %s: %s",
            chat_id,
            exc,
        )
        return False


async def execute_mute(
    bot,
    chat_id: int,
    user_id: int,
    message_id: int,
    reason: str,
) -> dict:
    """
    Execute the standard moderation action:

        1. Delete offending message.
        2. Mute member for 5 minutes.
        3. Send warning.

    Returns a small serializable result dictionary.
    """

    deleted = await delete_message(
        bot,
        chat_id,
        message_id,
    )

    muted = await mute_user(
        bot,
        chat_id,
        user_id,
    )

    warning = await send_warning(
        bot,
        chat_id,
        user_id,
        reason,
    )

    return {
        "deleted": deleted,
        "muted": muted,
        "warning": warning,
    }
