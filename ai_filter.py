import os
import json
from google import genai
from config import GEMINI_API_KEY

# Initialize the official Google GenAI client
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are a Telegram group moderation AI. 
Analyze the given message for toxicity, hate speech, severe insults, harassment, threats, scams, or explicit abuse.

You must reply with a valid JSON object ONLY. No markdown formatting (no ```json code blocks), no explanations, and no extra text.

Format:
{
  "action": "allow" or "block",
  "reason": "Short description of why it was blocked, or Safe if allowed",
  "severity": number from 0 to 100
}
"""

def moderate_message(message):
    """Sends text to Gemini to check for abuse or toxicity and returns a dict."""
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nMessage:\n{message}"
        )
        
        text = response.text.strip()
        
        # Clean markdown code blocks if the model accidentally includes them
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()

        result = json.loads(text)
        return result

    except Exception as e:
        print(f"⚠️ Gemini AI Filtering Error: {e}")
        return {
            "action": "allow",
            "reason": "AI Error / Fallback",
            "severity": 0
        }
