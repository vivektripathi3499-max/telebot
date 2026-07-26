import re

LINK_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+|discord\.gg/\S+|bit\.ly/\S+|tinyurl\.com/\S+)",
    re.IGNORECASE,
)


def contains_link(text: str) -> bool:
    if not text:
        return False

    return bool(LINK_PATTERN.search(text))
