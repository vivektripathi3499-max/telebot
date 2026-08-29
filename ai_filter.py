import os
import json
from google import genai
from google.genai import types
from PIL import Image
from config import GEMINI_API_KEY

# Initialize the official Google GenAI client with low-latency settings
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are an aggressive Telegram group moderation AI. 
Analyze the given message for:
1. Toxicity, hate speech, severe insults, harassment, threats, scams, or explicit abuse.
2. Direct or indirect solicitations for DMs, private chats, inbox messages, WhatsApp/Snapchat exchanges, or channel promotions.
3. Requests for sex videos, adult content, hookups, or explicit media.

Even if phrased subtly, casually, or disguised with spaces, symbols, or slang (e.g., "come inbox", "want fun", "dm for adult vids"), you must flag it.

Return ONLY a valid JSON object:
{
  "action": "allow" or "block",
  "reason": "Short description of why it was blocked, or Safe if allowed",
  "severity": number from 0 to 100
}
"""

VISION_SYSTEM_PROMPT = """
You are an aggressive Telegram group moderation AI inspecting media (image, sticker, GIF, or video) sent by a user.
Analyze the visual content for vulgar text (OCR), abusive drawings, hand gestures, hate symbols, or explicit/sexual/nude content.

Return ONLY a valid JSON object:
{
  "action": "allow" or "block",
  "reason": "Short description of why the media was blocked, or Safe if allowed",
  "severity": number from 0 to 100
}
"""

# Ultra-fast configuration using Gemini Flash with low token limits
FAST_CONFIG = types.GenerateContentConfig(
    temperature=0.1,
    max_output_tokens=60,
    response_mime_type="application/json",
)

def moderate_message(message):
    """Sends text to Gemini with ultra-fast json configuration and solicitation detection."""
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
        print(f"⚠️ Gemini AI Filtering Error: {e}")
        return {
            "action": "allow",
            "reason": "AI Error / Fallback",
            "severity": 0
        }

def moderate_image(file_path):
    """Handles images, stickers, GIFs, and videos for Gemini NSFW and explicit content detection."""
    uploaded_file_ref = None
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        # If it's a video file (MP4, WebM, MOV, etc.), upload it via the Files API
        if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            uploaded_file_ref = client.files.upload(file=file_path)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file_ref, VISION_SYSTEM_PROMPT],
                config=FAST_CONFIG
            )
        else:
            # Handle images and static/animated stickers (.jpg, .png, .webp)
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
        print(f"⚠️ Gemini Media/Video AI Filtering Error: {e}")
        return {
            "action": "allow",
            "reason": "AI Error / Fallback",
            "severity": 0
        }
    finally:
        # Clean up remote file reference from Gemini servers if a video was uploaded
        if uploaded_file_ref:
            try:
                client.files.delete(name=uploaded_file_ref.name)
            except Exception:
                pass
