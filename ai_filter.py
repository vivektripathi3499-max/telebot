import os
import json
from google import genai
from google.genai import types
from PIL import Image
from config import GEMINI_API_KEY

# Initialize the official Google GenAI client with low-latency settings
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Analyze the message for toxicity, hate speech, severe insults, harassment, threats, scams, or explicit abuse. Return ONLY a valid JSON object: {"action": "allow" or "block", "reason": "...", "severity": 0-100}"""

VISION_SYSTEM_PROMPT = """Analyze this image/sticker/GIF for vulgar text, abusive drawings, hand gestures, hate symbols, or explicit/sexual content. Return ONLY a valid JSON object: {"action": "allow" or "block", "reason": "...", "severity": 0-100}"""

# Ultra-fast configuration configuration using Gemini Flash with low token limits
FAST_CONFIG = types.GenerateContentConfig(
    temperature=0.1,
    max_output_tokens=60,
    response_mime_type="application/json",
)

def moderate_message(message):
    """Sends text to Gemini with ultra-fast json configuration."""
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
    """Sends image/sticker/GIF to Gemini with optimized sizing for maximum speed."""
    try:
        # Resize large images down to max 512px to accelerate network upload and inference time
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
        print(f"⚠️ Gemini Image AI Filtering Error: {e}")
        return {
            "action": "allow",
            "reason": "AI Error / Fallback",
            "severity": 0
        }
