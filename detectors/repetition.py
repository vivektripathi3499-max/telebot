import re
from collections import Counter


def repeated_character(text: str) -> bool:
    if not text:
        return False

    compact = re.sub(r"\s+", "", text)

    if len(compact) < 10:
        return False

    most_common = Counter(compact).most_common(1)

    if not most_common:
        return False

    _, count = most_common[0]

    return count / len(compact) >= 0.80


def repeated_word(text: str) -> bool:
    if not text:
        return False

    words = re.findall(
        r"\b[\w']+\b",
        text.lower(),
    )

    if len(words) < 5:
        return False

    most_common = Counter(words).most_common(1)

    if not most_common:
        return False

    _, count = most_common[0]

    return (
        count >= 5
        and count / len(words) >= 0.60
    )


def repeated_punctuation(text: str) -> bool:
    if not text:
        return False

    return bool(
        re.search(
            r"([!?.,])\1{7,}",
            text,
        )
    )


def is_repetition_spam(text: str) -> bool:
    return (
        repeated_character(text)
        or repeated_word(text)
        or repeated_punctuation(text)
    )
