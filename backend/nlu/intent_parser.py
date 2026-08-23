import os
import json
import httpx
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are a grocery list voice assistant. Your job is to parse user voice commands into structured JSON.

Always respond with ONLY valid JSON matching this exact schema:
{
  "intent": "<add_item|remove_item|search_item|list_items|mark_purchased|suggest_substitute|unknown>",
  "item": "<item name in lowercase, null if not applicable>",
  "quantity": <number, default 1>,
  "unit": "<unit string e.g. 'bottles', 'kg', 'packets', or empty string>",
  "category": "<dairy|produce|beverages|bakery|meat|grains|pantry|snacks|other>",
  "filters": {"brand": null, "max_price": null},
  "detected_language": "<en|hi|other>"
}

Rules:
- Detect the input language and set detected_language accordingly (en=English, hi=Hindi)
- Extract the intent regardless of phrasing variation
- Normalize item names to lowercase singular (e.g. "apples" → "apple", "bottles of water" → "water")
- Infer category from item name
- If quantity is mentioned, parse it (e.g. "2 bottles" → quantity:2, unit:"bottles")
- If you can't parse the command, set intent to "unknown"

Examples:
Input: "Add milk to my list"
Output: {"intent":"add_item","item":"milk","quantity":1,"unit":"","category":"dairy","filters":{"brand":null,"max_price":null},"detected_language":"en"}

Input: "I need apples"
Output: {"intent":"add_item","item":"apple","quantity":1,"unit":"","category":"produce","filters":{"brand":null,"max_price":null},"detected_language":"en"}

Input: "Add 2 bottles of water"
Output: {"intent":"add_item","item":"water","quantity":2,"unit":"bottles","category":"beverages","filters":{"brand":null,"max_price":null},"detected_language":"en"}

Input: "Remove milk from my list"
Output: {"intent":"remove_item","item":"milk","quantity":1,"unit":"","category":"dairy","filters":{"brand":null,"max_price":null},"detected_language":"en"}

Input: "What's on my list?"
Output: {"intent":"list_items","item":null,"quantity":1,"unit":"","category":"other","filters":{"brand":null,"max_price":null},"detected_language":"en"}

Input: "I want to buy bananas"
Output: {"intent":"add_item","item":"banana","quantity":1,"unit":"","category":"produce","filters":{"brand":null,"max_price":null},"detected_language":"en"}

Input: "I prefer almond milk instead of milk"
Output: {"intent":"suggest_substitute","item":"milk","quantity":1,"unit":"","category":"dairy","filters":{"brand":null,"max_price":null},"detected_language":"en"}

Input: "Mark eggs as purchased"
Output: {"intent":"mark_purchased","item":"egg","quantity":1,"unit":"","category":"dairy","filters":{"brand":null,"max_price":null},"detected_language":"en"}

Input: "दूध जोड़ो"
Output: {"intent":"add_item","item":"milk","quantity":1,"unit":"","category":"dairy","filters":{"brand":null,"max_price":null},"detected_language":"hi"}

Input: "सेब चाहिए"
Output: {"intent":"add_item","item":"apple","quantity":1,"unit":"","category":"produce","filters":{"brand":null,"max_price":null},"detected_language":"hi"}
"""

CONFIRMATION_TEMPLATES = {
    "en": {
        "add_item": "Added {quantity} {unit} {item} to your list ✓",
        "remove_item": "Removed {item} from your list ✓",
        "mark_purchased": "Marked {item} as purchased ✓",
        "list_items": "Here's your current list",
        "suggest_substitute": "Here are some alternatives for {item}",
        "unknown": "Sorry, I didn't catch that — try again?",
    },
    "hi": {
        "add_item": "{item} आपकी सूची में जोड़ा गया ✓",
        "remove_item": "{item} आपकी सूची से हटा दिया गया ✓",
        "mark_purchased": "{item} को खरीदा हुआ चिह्नित किया गया ✓",
        "list_items": "यहाँ आपकी वर्तमान सूची है",
        "suggest_substitute": "{item} के कुछ विकल्प",
        "unknown": "माफ़ करें, मैं समझ नहीं पाया — फिर से कोशिश करें?",
    },
}


async def parse_intent(text: str, response_language: str = "en") -> dict:
    """
    Call Groq to parse a voice command into structured intent JSON.
    Retries across supported models. Returns a dict with intent schema.
    """
    models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
    for model_name in models:
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=400,
                timeout=12,
            )
            raw = response.choices[0].message.content.strip()
            # Strip reasoning / think tags if present
            import re
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            # Strip markdown code fences if present
            if "```" in raw:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
                if match:
                    raw = match.group(1)
            # Find the JSON block
            json_match = re.search(r"\{[\s\S]*\}", raw)
            if json_match:
                raw = json_match.group(0)
            intent_data = json.loads(raw.strip())
            return intent_data
        except Exception as e:
            print(f"Error parsing intent with model {model_name}: {e}")
            continue

    return {
        "intent": "unknown",
        "item": None,
        "quantity": 1,
        "unit": "",
        "category": "other",
        "filters": {"brand": None, "max_price": None},
        "detected_language": "en",
    }


def build_confirmation(intent_data: dict, response_language: str = "en") -> str:
    """Build a human-readable confirmation string in the chosen language."""
    lang = response_language if response_language in CONFIRMATION_TEMPLATES else "en"
    templates = CONFIRMATION_TEMPLATES[lang]
    intent = intent_data.get("intent", "unknown")
    template = templates.get(intent, templates["unknown"])

    unit = intent_data.get("unit", "") or ""
    unit_str = f"{unit} " if unit else ""

    return template.format(
        item=intent_data.get("item") or "",
        quantity=intent_data.get("quantity", 1),
        unit=unit_str.strip(),
    )
