"""
food.py - scans a photo of a meal and estimates calories and nutrients.

Uses Google's Gemini API (free tier), which can "see" images.
The key and model names live in the .env file.
"""

import base64
import io
import json
import os

import requests
from dotenv import load_dotenv
from PIL import Image

from coach import CoachError

load_dotenv()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODELS = "gemini-3.1-flash-lite,gemini-3.5-flash"

FOOD_PROMPT = """You are a friendly nutrition assistant for a health coach app used by people
with PCOS and people recovering from body-shaming. Look at this photo of a meal.

1. Identify each food item (be specific about Indian / Kerala dishes, e.g. "Kerala matta rice",
   "sambar", "appam", "fish curry", "thoran").
2. Estimate the portion size you can see and its calories and macronutrients.
3. Give ONE short, positive, PCOS-friendly tip (e.g. adding protein or fibre). Never call any food
   "bad" or "junk", and never make the user feel guilty.

{note}

Reply with ONLY valid JSON in exactly this format:
{{
  "items": [
    {{"name": "Kerala matta rice", "portion": "1 cup (150 g)", "calories": 200,
      "protein_g": 4, "carbs_g": 44, "fat_g": 1, "fibre_g": 2}}
  ],
  "tip": "short positive tip",
  "confidence": "high | medium | low"
}}
If the photo does not show food, return {{"items": [], "tip": "I couldn't see any food in this photo.", "confidence": "low"}}.
"""


def _gemini_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key.startswith("paste"):
        raise CoachError(
            "No Gemini key found. Open the .env file and paste your Gemini key "
            "after GEMINI_API_KEY=, then restart the app."
        )
    return key


def _prepare_image(image_bytes: bytes) -> str:
    """Shrink big phone photos (faster + uses less of the free quota) and return base64 JPEG."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode()


def _parse_json(text: str) -> dict:
    """Read the AI's JSON reply, even if it wrapped it in ```json ... ``` fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start:end + 1])

    items = []
    for item in data.get("items", []):
        items.append({
            "name": str(item.get("name", "Food")),
            "portion": str(item.get("portion", "")),
            "calories": round(float(item.get("calories", 0) or 0)),
            "protein_g": round(float(item.get("protein_g", 0) or 0), 1),
            "carbs_g": round(float(item.get("carbs_g", 0) or 0), 1),
            "fat_g": round(float(item.get("fat_g", 0) or 0), 1),
            "fibre_g": round(float(item.get("fibre_g", 0) or 0), 1),
        })
    for item in items:
        item["servings"] = 1.0  # you can change this if you ate more or less than the photo shows
    return {"items": items, "tip": data.get("tip", ""), "confidence": data.get("confidence", "medium")}


def scaled(item: dict) -> dict:
    """The item's numbers multiplied by how many servings you actually ate."""
    k = float(item.get("servings") or 1)
    out = dict(item)
    for key in ("calories", "protein_g", "carbs_g", "fat_g", "fibre_g"):
        out[key] = round(float(item.get(key) or 0) * k, 1)
    out["calories"] = round(out["calories"])
    return out


def macro_check(item: dict) -> str | None:
    """Protein and carbs have about 4 kcal per gram and fat about 9. If the AI's calories are far from
    what its own macros add up to, one of the numbers is probably wrong, so we say so."""
    kcal = float(item.get("calories") or 0)
    from_macros = 4 * float(item.get("protein_g") or 0) + 4 * float(item.get("carbs_g") or 0) + 9 * float(item.get("fat_g") or 0)
    if kcal < 40 or from_macros == 0:
        return None
    if abs(from_macros - kcal) / kcal > 0.3:
        return f"Numbers may not add up: the nutrients suggest about {from_macros:.0f} kcal, not {kcal:.0f}."
    return None


def scan_meal(image_bytes: bytes, note: str = "") -> dict:
    """Send a meal photo to Gemini and return {"items": [...], "tip": str, "confidence": str}."""
    note_text = f'The user added this note about the meal: "{note}". Use it to improve your estimate.' if note else ""
    body = {
        "contents": [{
            "parts": [
                {"text": FOOD_PROMPT.format(note=note_text)},
                {"inline_data": {"mime_type": "image/jpeg", "data": _prepare_image(image_bytes)}},
            ]
        }],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    headers = {"x-goog-api-key": _gemini_key(), "Content-Type": "application/json"}

    models = [m.strip() for m in os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODELS).split(",") if m.strip()]
    last_error = "No Gemini model is configured."
    for model in models:
        try:
            response = requests.post(GEMINI_URL.format(model=model), headers=headers, json=body, timeout=60)
        except requests.RequestException:
            raise CoachError("Couldn't reach Gemini. Check your internet connection and try again.")

        if response.status_code in (400, 403) and "API key" in response.text:
            raise CoachError("Your Gemini key was rejected. Check GEMINI_API_KEY in your .env file.")
        if response.status_code == 429:
            last_error = "You've hit the free Gemini limit for now. Wait a minute and try again."
            continue
        if response.status_code != 200:
            last_error = f"{model} returned an error ({response.status_code}): {response.text[:200]}"
            continue

        try:
            parts = response.json()["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return _parse_json(text)
        except (KeyError, IndexError, ValueError, TypeError):
            last_error = "The AI couldn't read this photo clearly. Try a brighter, closer photo."

    raise CoachError(last_error)
