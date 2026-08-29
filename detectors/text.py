from detectors.links import (
    has_link,
    has_telegram_link,
)

from detectors.promotion import (
    is_promotion,
)

from detectors.repetition import (
    is_repetition_spam,
)


def detect_text_violation(text: str):
    """
    Fast, local text moderation.

    Returns a moderation dictionary or None.
    """

    if not text:
        return None

    if has_telegram_link(text):
        return {
            "action": "mute",
            "reason": "Telegram group/channel promotion",
            "severity": 90,
        }

    if has_link(text):
        return {
            "action": "mute",
            "reason": "Unauthorized link",
            "severity": 80,
        }

    if is_promotion(text):
        return {
            "action": "mute",
            "reason": "Promotion or solicitation",
            "severity": 85,
        }

    if is_repetition_spam(text):
        return {
            "action": "mute",
            "reason": "Repetition/flood spam",
            "severity": 75,
        }

    return None
