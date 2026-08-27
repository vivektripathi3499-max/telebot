from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)
import time
import asyncio
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from collections import defaultdict

from telegram.error import BadRequest
from config import BOT_TOKEN, ALLOWED_GROUPS
from welcome import welcome
from moderation import contains_link
from spam import check_spam
from ai_filter import moderate_message
from strikes import add_strike
from logger import save_log, send_log

# Specific banned words list (checked case-insensitively)
EXPLICIT_BANNED_WORDS = ["tmkc", "bsdk", "madarchot", "bhosadike", "Bkl", "bkl", "Mdrcd", "Mdrchd"]

# Banned sticker packs (optional: add known abusive pack shortnames here)
BANNED_STICKER_SETS = set()

# In-memory dictionary for rapid sticker flood rate-limiting: {user_id: [timestamp1, timestamp2, ...]}
user_sticker_timestamps = defaultdict(list)
STICKER_RATE_LIMIT_COUNT = 3
STICKER_RATE_LIMIT_WINDOW = 5.0  # seconds


# --- KEEP-ALIVE WEB SERVER FOR RENDER FREE TIER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Telegram Moderator Bot is active and running!")
        
    def log_message(self, format, *args):
        return

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def start_keep_alive():
    t = threading.Thread(target=run_http_server)
    t.daemon = True
    t.start()


async def is_admin(chat, user_id):
    try:
        member = await chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def has_excessive_special_chars(text):
    """Checks if the text contains more than 2 special characters/symbols."""
    special_chars = re.findall(r'[^a-zA-Z0-9\s]', text)
    return len(special_chars) > 2


async def punish_user(update, context, chat, user, reason):
    """Blazing fast punishment pipeline: Deletes message, mutes for 5 mins, and warns."""
    # 1. Delete instantly
    try:
        await update.message.delete()
    except BadRequest:
        pass
        
    # 2. Mute the user for 5 minutes (300 seconds)
    try:
        mute_until = int(time.time()) + 300
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=mute_until
        )
    except Exception:
        pass
        
    # 3. Send warning
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"⚠️ **{user.full_name}** was muted for 5 minutes. Reason: *{reason}*",
            parse_mode="Markdown"
        )
    except Exception:
        pass


def check_sticker_flood(user_id):
    """Returns True if the user is flooding stickers too fast."""
    now = time.time()
    timestamps = user_sticker_timestamps[user_id]
    timestamps = [t for t in timestamps if now - t < STICKER_RATE_LIMIT_WINDOW]
    timestamps.append(now)
    user_sticker_timestamps[user_id] = timestamps
    return len(timestamps) > STICKER_RATE_LIMIT_COUNT


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming stickers, checks for flood spam or prohibited sticker packs."""
    if not update.message or not update.message.sticker:
        return

    chat = update.effective_chat
    user = update.effective_user
    sticker = update.message.sticker

    # Ignore private chats, unauthorized groups, bots, and admins instantly
    if chat.type == "private":
        return
    if ALLOWED_GROUPS and chat.id not in ALLOWED_GROUPS:
        return
    if user.is_bot:
        return
    if await is_admin(chat, user.id):
        return

    reason = None

    # 1. Check if sticker belongs to a banned pack
    if sticker.set_name and sticker.set_name in BANNED_STICKER_SETS:
        reason = "Prohibited sticker pack detected"

    # 2. Check for sticker flooding / spamming
    elif check_sticker_flood(user.id):
        reason = "Sticker spamming / flooding"

    if reason:
        await punish_user(update, context, chat, user, reason)
        strikes, action = add_strike(chat.id, user.id, user.username or user.full_name, reason)
        save_log(chat.id, user.id, action, reason, 85)
        await send_log(context, user.username or user.full_name, user.id, action, reason, 85)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat = update.effective_chat
    user = update.effective_user
    text = update.message.text
    text_lower = text.lower()

    # Ignore private chats, unauthorized groups, bots, and admins instantly
    if chat.type == "private":
        return
    if ALLOWED_GROUPS and chat.id not in ALLOWED_GROUPS:
        return
    if user.is_bot:
        return
    if await is_admin(chat, user.id):
        return

    # ==========================================
    # PHASE 1: INSTANT LOCAL CHECKS (0-millisecond delay)
    # ==========================================
    
    # 1. Check explicit banned words instantly
    if any(word in text_lower for word in EXPLICIT_BANNED_WORDS):
        await punish_user(update, context, chat, user, "Use of prohibited abusive words")
        strikes, action = add_strike(chat.id, user.id, user.username or user.full_name, "Banned word detected")
        save_log(chat.id, user.id, action, "Banned word detected", 90)
        await send_log(context, user.username or user.full_name, user.id, action, "Banned word detected", 90)
        return

    # 2. Check for more than 2 special characters instantly
    if has_excessive_special_chars(text):
        await punish_user(update, context, chat, user, "Excessive special characters/symbols spam")
        strikes, action = add_strike(chat.id, user.id, user.username or user.full_name, "Excessive special characters")
        save_log(chat.id, user.id, action, "Excessive special characters", 80)
        await send_log(context, user.username or user.full_name, user.id, action, "Excessive special characters", 80)
        return

    # 3. Check Links instantly
    if contains_link(text):
        await punish_user(update, context, chat, user, "Unauthorized link detected")
        strikes, action = add_strike(chat.id, user.id, user.username or user.full_name, "Link detected")
        save_log(chat.id, user.id, action, "Link detected", 80)
        await send_log(context, user.username or user.full_name, user.id, action, "Link detected", 80)
        return

    # 4. Check Spam patterns instantly
    spam = check_spam(chat.id, user.id, text)
    if spam["spam"]:
        await punish_user(update, context, chat, user, spam["reason"])
        strikes, action = add_strike(chat.id, user.id, user.username or user.full_name, spam["reason"])
        save_log(chat.id, user.id, action, spam["reason"], spam["severity"])
        await send_log(context, user.username or user.full_name, user.id, action, spam["reason"], spam["severity"])
        return

    # ==========================================
    # PHASE 2: NON-BLOCKING BACKGROUND AI WORKER
    # ==========================================
    async def run_ai_background():
        try:
            loop = asyncio.get_running_loop()
            ai = await loop.run_in_executor(None, moderate_message, text)
            
            if ai and ai.get("action") != "allow":
                await punish_user(update, context, chat, user, ai.get("reason", "AI Moderation Flag"))
                add_strike(chat.id, user.id, user.username or user.full_name, ai.get("reason", "AI Flag"))
                save_log(chat.id, user.id, "strike", ai.get("reason", "AI Flag"), ai.get("severity", 50))
        except Exception as e:
            print(f"Background AI worker exception: {e}")

    asyncio.create_task(run_ai_background())


def main():
    # Start the keep-alive server so Render detects an active port binding
    start_keep_alive()

    app = Application.builder().token(BOT_TOKEN).connect_timeout(60.0).read_timeout(60.0).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running at maximum velocity with sticker protection...")
    app.run_polling()


if __name__ == "__main__":
    main()
