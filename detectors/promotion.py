PROMOTION_PHRASES = (
    "join my group",
    "join my channel",
    "join our group",
    "join our channel",
    "dm me",
    "pm me",
    "message me",
    "inbox me",
    "contact me",
    "add me",
    "link in bio",
    "check my bio",
    "whatsapp me",
)


def is_promotion(text: str) -> bool:
    if not text:
        return False

    lowered = text.lower()

    return any(
        phrase in lowered
        for phrase in PROMOTION_PHRASES
    )
