from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ALLOWED_GROUPS
from welcome import welcome
from moderation import contains_link
from spam import check_spam
from ai_filter import moderate_message
from strikes import add_strike
from logger import save_log, send_log


async def is_admin(chat, user_id):
    member = await chat.get_member(user_id)
    return member.status in ("administrator", "creator")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    chat = update.effective_chat
    user = update.effective_user
    text = update.message.text

    print(f"Chat ID: {chat.id}")
    print(f"Chat Type: {chat.type}")
    print(f"User: {user.full_name}")


    # Ignore private chats
    if chat.type == "private":
        return

    # Ignore groups that are not allowed
    if ALLOWED_GROUPS and chat.id not in ALLOWED_GROUPS:
        return

    # Ignore messages from bots
    if user.is_bot:
        return

    # Ignore owner and admins
    if await is_admin(chat, user.id):
        return


    # Link detection
    if contains_link(text):
        await update.message.delete()

        strikes, action = add_strike(
            chat.id,
            user.id,
            user.username or user.full_name,
            "Link detected"
        )

        save_log(chat.id, user.id, action, "Link detected", 80)
        await send_log(
            context,
            user.username or user.full_name,
            user.id,
            action,
            "Link detected",
            80,
        )

        return

    # Spam detection
    spam = check_spam(chat.id, user.id, text)

    if spam["spam"]:
        await update.message.delete()

        strikes, action = add_strike(
            chat.id,
            user.id,
            user.username or user.full_name,
            spam["reason"],
        )

        save_log(
            chat.id,
            user.id,
            action,
            spam["reason"],
            spam["severity"],
        )

        await send_log(
            context,
            user.username or user.full_name,
            user.id,
            action,
            spam["reason"],
            spam["severity"],
        )

        return

    # AI moderation
    ai = moderate_message(text)

    if ai["action"] != "allow":

        await update.message.delete()

        strikes, action = add_strike(
            chat.id,
            user.id,
            user.username or user.full_name,
            ai["reason"],
        )

        save_log(
            chat.id,
            user.id,
            action,
            ai["reason"],
            ai["severity"],
        )

        await send_log(
            context,
            user.username or user.full_name,
            user.id,
            action,
            ai["reason"],
            ai["severity"],
        )


def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
