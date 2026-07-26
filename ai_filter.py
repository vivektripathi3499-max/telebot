import json
from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are a Telegram moderation AI.

Reply ONLY with valid JSON.

Example:

{
  "action":"allow",
  "reason":"Safe",
  "severity":0
}

Rules:

- allow = safe message
- delete = abuse, insults, spam, phishing, scams
- ban = terrorism, child exploitation, violent threats

No markdown.

No explanation.

No extra text.
"""

def moderate_message(message):

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"{SYSTEM_PROMPT}\n\nMessage:\n{message}"
    )

    text = response.text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)

    except Exception:

        return {
            "action":"allow",
            "reason":"AI Error",
            "severity":0
        }
