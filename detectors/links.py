import re


URL_RE = re.compile(
    r"(?:https?://|www\.|t\.me/|telegram\.me/)\S+",
    re.IGNORECASE,
)


def has_link(text: str) -> bool:
    if not text:
        return False

    return bool(URL_RE.search(text))


def has_telegram_link(text: str) -> bool:
    if not text:
        return False

    lowered = text.lower()

    return (
        "t.me/" in lowered
        or "telegram.me/" in lowered
    )

