import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ADMIN_LOG_CHAT_ID = int(os.getenv("ADMIN_LOG_CHAT_ID", "0"))

MUTE_MINUTES = int(os.getenv("MUTE_MINUTES", "5"))
MAX_STRIKES = int(os.getenv("MAX_STRIKES", "5"))

ALLOWED_GROUPS = [
    int(group_id)
    for group_id in os.getenv("ALLOWED_GROUPS", "").split(",")
    if group_id.strip()
]
