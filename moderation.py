"""
Telegram moderation utilities.

This module contains fast, local checks only.
It intentionally has no Discord dependency.
"""

import re
from urllib.parse import urlparse


# Common URL patterns.
LINK_PATTERN = re.compile(
    r"""
    (?:
        https?://[^\s<>()]+
        |
        www\.[^\s<>()]+
        |
        t\.me/[^\s<>()]+
        |
        telegram\.me/[^\s<>()]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# Telegram invite/link indicators.
TELEGRAM_LINK_PATTERN = re.compile(
    r"""
    (?:
        https?://
        |
        www\.
    )?
    (?:
        t\.me
        |
        telegram\.me
    )
    /
    [^\s<>()]+
    """,
    re.IGNORECASE | re.VERBOSE,
)


def contains_link(text: str) -> bool:
    """
    Return True if the supplied text contains a URL
    or common Telegram link.
    """

    if not text:
        return False

    return bool(LINK_PATTERN.search(text))


def contains_telegram_link(text: str) -> bool:
    """
    Return True if the supplied text contains a Telegram link.
    """

    if not text:
        return False

    return bool(TELEGRAM_LINK_PATTERN.search(text))


def extract_links(text: str) -> list[str]:
    """
    Return all detected links from text.
    """

    if not text:
        return []

    return LINK_PATTERN.findall(text)


def get_domain(url: str) -> str:
    """
    Extract a normalized domain from a URL.
    """

    if not url:
        return ""

    value = url.strip()

    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    try:
        parsed = urlparse(value)

        domain = parsed.netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def contains_promotion(text: str) -> bool:
    """
    Detect common promotional / contact phrases.

    This is deliberately simple and fast. More advanced
    promotion classification can be performed by the AI layer.
    """

    if not text:
        return False

    text_lower = text.lower()

    promotion_phrases = (
        "link in bio",
        "check bio",
        "dm me",
        "message me",
        "pm me",
        "inbox me",
        "contact me",
        "add me",
        "join my group",
        "join my channel",
        "join our group",
        "join our channel",
        "telegram.me",
        "t.me/",
    )

    return any(
        phrase in text_lower
        for phrase in promotion_phrases
    )
