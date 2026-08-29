import os
import json
from google import genai
from google.genai import types
from PIL import Image
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are an ultra-strict, aggressive Telegram group moderation AI. 
Analyze the message for any form of:
1. Humiliation, severe insults, bullying, toxic remarks, or hate speech.
2. Mother abuse, family slurs, or explicit curses.
3. Sexual content, requests for sex, adult videos, hookups, or DMs/inbox solicitation.

Even if disguised with spacing, symbols, or casual slang, flag it.

Return ONLY a valid JSON object:
{
  "action": "allow" or "block",
  "reason": "Short description of violation, or Safe if allowed",
  "severity": number from 0 to 100
}
"""

VISION_SYSTEM_PROMPT = """
You are an ultra-strict Telegram group moderation AI inspecting an image, sticker, GIF, or video sent by a user.
Analyze the visual content for nudity, sexual acts, explicit material, vulgar OCR text, hate symbols, or hand gestures.

Return ONLY a valid JSON object:
{
  "action": "allow" or "block",
  "reason": "Short description of violation, or Safe if allowed",
  "severity": number from 0 to 100
}
"""

FAST_CONFIG = types.GenerateContentConfig(
    temperature=0.0,
    max_output_tokens=50,
    response_mime_type="application/json",
)

def moderate_message(message):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nMessage:\n{message}",
            config=FAST_CONFIG
        )
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return {"action": "allow", "reason": "Fallback", "severity": 0}

def moderate_image(file_path):
    uploaded_file_ref = None
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            uploaded_file_ref = client.files.upload(file=file_path)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file_ref, VISION_SYSTEM_PROMPT],
                config=FAST_CONFIG
            )
        else:
            with Image.open(file_path) as img:
                img.verify()
            image = Image.open(file_path)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.thumbnail((512, 512))
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image, VISION_SYSTEM_PROMPT],
                config=FAST_CONFIG
            )
        
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ Media AI Error: {e}")
        return {"action": "allow", "reason": "Fallback", "severity": 0}
    finally:
        if uploaded_file_ref:
            try: client.files.delete(name=uploaded_file_ref.name)
            except: pass
