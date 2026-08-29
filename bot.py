from collections import defaultdict
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import re
import threading
import time
from ai_filter import moderate_image, moderate_message
from config import ALLOWED_GROUPS, BOT_TOKEN
from logger import save_log, send_log
from moderation import contains_link
from spam import check_spam
from strikes import add_strike
from telegram import ChatPermissions, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)
from welcome import welcome

EXPLICIT_BANNED_WORDS = [
    "tmkc",
    "bsdk",
    "madarchot",
    "bhosadike",
    "Bkl",
    "bkl",
    "Mdrcd",
    "Mdrchd",
    "Saala",
    "Saali",
    "Add me",
    "Added",
    "Msg me",
]

BANNED_STICKER_SETS = set()
RESTRICTED_STICKER_EMOJIS = {"🖕", "🤬", "💩"}

PROMOTION_PHRASES = [
    "link in bio",
    "check bio",
    "dm me",
    "add me on",
    "telegram.me",
    "t.me",
    "whatsapp",
    "snapchat",
]

user_sticker_timestamps = defaultdict(list)
STICKER_RATE_LIMIT_COUNT = 3
STICKER_RATE_LIMIT_WINDOW = 5.0

# --- IN-MEMORY ADMIN CACHE TO SPEED UP LOOKUPS (TTL = 5 mins) ---
admin_cache = {}
ADMIN_CACHE_TTL = 300


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
  now = time.time()
  cache_key = (chat.id, user_id)

  # Check cache first for 0ms lookup latency
  if cache_key in admin_cache:
    is_adm, timestamp = admin_cache[cache_key]
    if now - timestamp < ADMIN_CACHE_TTL:
      return is_adm

  # Fetch from Telegram API only if cache expired or missing
  try:
    member = await chat.get_member(user_id)
    result = member.status in ("administrator", "creator")
    admin_cache[cache_key] = (result, now)
    return result
  except Exception:
    return False


def has_excessive_special_chars(text):
  special_chars = re.findall(r"[^a-zA-Z0-9\s]", text)
  return len(special_chars) > 2


async def punish_user(update, context, chat, user, reason):
  """Instant punishment pipeline: Deletes message and mutes user for 5 minutes with 0ms delay."""
  try:
    await update.message.delete()
  except BadRequest:
    pass

  try:
    mute_until = int(time.time()) + 300
    await context.bot.restrict_chat_member(
        chat_id=chat.id,
        user_id=user.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=mute_until,
    )
  except Exception:
    pass

  try:
    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            f"⚠️ **{user.full_name}** was muted for 5 minutes. Reason:"
            f" *{reason}*"
        ),
        parse_mode="Markdown",
    )
  except Exception:
    pass


def check_sticker_flood(user_id):
  now = time.time()
  timestamps = user_sticker_timestamps[user_id]
  timestamps = [t for t in timestamps if now - t < STICKER_RATE_LIMIT_WINDOW]
  timestamps.append(now)
  user_sticker_timestamps[user_id] = timestamps
  return len(timestamps) > STICKER_RATE_LIMIT_COUNT


# --- NON-BLOCKING BACKGROUND LOGGING PIPELINE ---
async def async_log_pipeline(
    context, chat_id, user, reason, severity, is_strike=True
):
  try:
    name = user.username or user.full_name
    if is_strike:
      _, action = add_strike(chat_id, user.id, name, reason)
    else:
      action = "mute"
    save_log(chat_id, user.id, action, reason, severity)
    await send_log(context, name, user.id, action, reason, severity)
  except Exception as e:
    print(f"Logging pipeline error: {e}")


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message or not update.message.sticker:
    return

  chat = update.effective_chat
  user = update.effective_user
  sticker = update.message.sticker

  if (
      chat.type == "private"
      or (ALLOWED_GROUPS and chat.id not in ALLOWED_GROUPS)
      or user.is_bot
      or await is_admin(chat, user.id)
  ):
    return

  reason = None
  if sticker.set_name and sticker.set_name in BANNED_STICKER_SETS:
    reason = "Prohibited sticker pack detected"
  elif sticker.emoji and sticker.emoji in RESTRICTED_STICKER_EMOJIS:
    reason = "Inappropriate emoji attached to sticker"
  elif check_sticker_flood(user.id):
    reason = "Sticker spamming / flooding"

  if reason:
    await punish_user(update, context, chat, user, reason)
    asyncio.create_task(async_log_pipeline(context, chat.id, user, reason, 85))
    return

  # RAM-backed /tmp path for maximum speed file processing
  async def run_sticker_ai_background():
    file_path = f"/tmp/temp_sticker_{user.id}_{int(time.time())}.webp"
    try:
      file = await sticker.get_file()
      await file.download_to_drive(file_path)
      loop = asyncio.get_running_loop()
      ai = await loop.run_in_executor(None, moderate_image, file_path)

      if ai and ai.get("action") != "allow":
        ai_reason = ai.get("reason", "NSFW / Explicit sexual sticker content detected")
        await punish_user(update, context, chat, user, ai_reason)
        await async_log_pipeline(
            context,
            chat.id,
            user,
            ai_reason,
            ai.get("severity", 90),
            is_strike=True,
        )
    except Exception as e:
      print(f"Background Sticker AI error: {e}")
    finally:
      if os.path.exists(file_path):
        try:
          os.remove(file_path)
        except Exception:
          pass

  asyncio.create_task(run_sticker_ai_background())


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message:
    return

  chat = update.effective_chat
  user = update.effective_user
  msg = update.message

  if (
      chat.type == "private"
      or (ALLOWED_GROUPS and chat.id not in ALLOWED_GROUPS)
      or user.is_bot
      or await is_admin(chat, user.id)
  ):
    return

  caption = msg.caption or ""
  if contains_link(caption) or any(
      p in caption.lower() for p in PROMOTION_PHRASES
  ):
    reason = "Unauthorized link or promotion in media caption"
    await punish_user(update, context, chat, user, reason)
    asyncio.create_task(async_log_pipeline(context, chat.id, user, reason, 85))
    return

  media_file = None
  file_ext = ".jpg"

  if msg.photo:
    media_file = await msg.photo[-1].get_file()
    file_ext = ".jpg"
  elif msg.animation:
    media_file = await msg.animation.get_file()
    file_ext = ".mp4"
  elif msg.video:
    media_file = await msg.video.get_file()
    file_ext = ".mp4"
  elif msg.document:
    mime = msg.document.mime_type or ""
    if "image" in mime or "video" in mime or mime == "application/octet-stream":
      media_file = await msg.document.get_file()
      file_ext = ".mp4" if "video" in mime else ".jpg"

  if not media_file:
    return

  async def run_media_ai_background():
    file_path = f"/tmp/temp_media_{user.id}_{int(time.time())}{file_ext}"
    try:
      await media_file.download_to_drive(file_path)
      loop = asyncio.get_running_loop()
      ai = await loop.run_in_executor(None, moderate_image, file_path)

      if ai and ai.get("action") != "allow":
        ai_reason = ai.get("reason", "NSFW / Explicit media content detected")
        await punish_user(update, context, chat, user, ai_reason)
        await async_log_pipeline(
            context,
            chat.id,
            user,
            ai_reason,
            ai.get("severity", 95),
            is_strike=True,
        )
    except Exception as e:
      print(f"Background Media AI error: {e}")
    finally:
      if os.path.exists(file_path):
        try:
          os.remove(file_path)
        except Exception:
          pass

  asyncio.create_task(run_media_ai_background())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message or not update.message.text:
    return

  chat = update.effective_chat
  user = update.effective_user
  text = update.message.text
  text_lower = text.lower()
  
  # Normalize text to catch spacing/symbol evasion tactics
  text_clean = re.sub(r'[\s\-_.,]+', '', text_lower)

  if (
      chat.type == "private"
      or (ALLOWED_GROUPS and chat.id not in ALLOWED_GROUPS)
      or user.is_bot
      or await is_admin(chat, user.id)
  ):
    return

  normalized_banned = [re.sub(r'[\s\-_.,]+', '', w.lower()) for w in EXPLICIT_BANNED_WORDS]

  if any(word in text_lower for word in EXPLICIT_BANNED_WORDS) or any(nb in text_clean for nb in normalized_banned if len(nb) > 2):
    reason = "Use of prohibited abusive words"
    await punish_user(update, context, chat, user, reason)
    asyncio.create_task(async_log_pipeline(context, chat.id, user, reason, 90))
    return

  is_evading = any(phrase in text_lower for phrase in PROMOTION_PHRASES)
  if contains_link(text) or is_evading:
    reason = "Unauthorized link, channel promotion, or DM solicitation"
    await punish_user(update, context, chat, user, reason)
    asyncio.create_task(async_log_pipeline(context, chat.id, user, reason, 85))
    return

  if has_excessive_special_chars(text):
    reason = "Excessive special characters spam"
    await punish_user(update, context, chat, user, reason)
    asyncio.create_task(async_log_pipeline(context, chat.id, user, reason, 80))
    return

  spam = check_spam(chat.id, user.id, text)
  if spam["spam"]:
    await punish_user(update, context, chat, user, spam["reason"])
    asyncio.create_task(
        async_log_pipeline(
            context, chat.id, user, spam["reason"], spam["severity"]
        )
    )
    return

  async def run_ai_background():
    try:
      loop = asyncio.get_running_loop()
      ai = await loop.run_in_executor(None, moderate_message, text)

      if ai and ai.get("action") != "allow":
        ai_reason = ai.get("reason", "AI Moderation Flag")
        await punish_user(update, context, chat, user, ai_reason)
        await async_log_pipeline(
            context,
            chat.id,
            user,
            ai_reason,
            ai.get("severity", 50),
            is_strike=True,
        )
    except Exception as e:
      print(f"Background AI worker exception: {e}")

  asyncio.create_task(run_ai_background())


def main():
  start_keep_alive()

  app = (
      Application.builder()
      .token(BOT_TOKEN)
      .connect_timeout(15.0)
      .read_timeout(15.0)
      .build()
  )

  app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
  app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
  app.add_handler(
      MessageHandler(
          filters.PHOTO | filters.ANIMATION | filters.VIDEO | filters.Document.ALL, handle_media
      )
  )
  app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

  print(
      "Lightning-fast bot online with Admin Cache TTL, RAM disk files, and"
      " active NSFW protection!"
  )
  app.run_polling()


if __name__ == "__main__":
  main()
