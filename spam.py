import time
from collections import defaultdict
import emoji

user_history = defaultdict(list)

MESSAGE_WINDOW = 10
MAX_MESSAGES = 5
MAX_DUPLICATES = 3

EMOJI_WARNING = 15
EMOJI_LIMIT = 50


def count_emojis(text: str) -> int:
    return emoji.emoji_count(text)


def check_spam(chat_id, user_id, message):

    now = time.time()

    key = (chat_id, user_id)

    history = user_history[key]

    history[:] = [
        item for item in history
        if now - item["time"] <= MESSAGE_WINDOW
    ]

    history.append({
        "text": message.lower().strip(),
        "time": now
    })

    # Flood detection
    if len(history) > MAX_MESSAGES:
        return {
            "spam": True,
            "reason": "Flooding",
            "severity": 90,
            "strikes": 2
        }

    # Duplicate detection
    duplicate_count = sum(
        1 for item in history
        if item["text"] == message.lower().strip()
    )

    if duplicate_count >= MAX_DUPLICATES:
        return {
            "spam": True,
            "reason": "Repeated Message",
            "severity": 70,
            "strikes": 1
        }

    # Emoji spam detection
    emoji_count = count_emojis(message)

    if emoji_count >= EMOJI_LIMIT:
        return {
            "spam": True,
            "reason": f"Emoji Spam ({emoji_count} emojis)",
            "severity": 95,
            "strikes": 2
        }

    if emoji_count > EMOJI_WARNING:
        return {
            "spam": True,
            "reason": f"Too Many Emojis ({emoji_count})",
            "severity": 60,
            "strikes": 1
        }

    return {
        "spam": False
    }
