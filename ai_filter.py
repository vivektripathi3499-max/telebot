import os
import json
from google import genai
from PIL import Image
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

VISION_SYSTEM_PROMPT = """
You are a Telegram group moderation AI inspecting a sticker image sent by a user.
Analyze the sticker image for vulgar text (OCR), abusive drawings, hand gestures, hate symbols, or explicit/sexual content.

You must reply with a valid JSON object ONLY. No markdown formatting (no ```json code blocks), no explanations, and no extra text.

Format:
{
  "action": "allow" or "block",
  "reason": "Short description of why the sticker was blocked, or Safe if allowed",
  "severity": number from 0 to 100
}
"""

def moderate_message(message):
    """Sends text to Gemini to check for abuse or toxicity and returns a dict."""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nMessage:\n{message}"
        )
        
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()

        return json.loads(text)

    except Exception as e:
        print(f"⚠️ Gemini AI Filtering Error: {e}")
        return {
            "action": "allow",
            "reason": "AI Error / Fallback",
            "severity": 0
        }

def moderate_image(file_path):
    """Sends a sticker image to Gemini to check for visual vulgarity or text abuse."""
    try:
        image = Image.open(file_path)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image, VISION_SYSTEM_PROMPT]
        )
        
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()

        return json.loads(text)

    except Exception as e:
        print(f"⚠️ Gemini Image AI Filtering Error: {e}")
        return {
            "action": "allow",
            "reason": "AI Error / Fallback",
            "severity": 0
        }
