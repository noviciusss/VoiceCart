import base64
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import AsyncGroq
from dotenv import load_dotenv

from db import get_pool
from nlu.intent_parser import parse_intent, build_confirmation

load_dotenv()

router = APIRouter(tags=["command"])
groq_client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])

# Load substitutes map once
_SUBS_PATH = Path(__file__).parent.parent / "nlu" / "substitutes.json"
SUBSTITUTES: dict[str, list[str]] = json.loads(_SUBS_PATH.read_text())


class CommandRequest(BaseModel):
    session_id: str
    text: str | None = None
    audio_base64: str | None = None
    response_language: str = "en"  # "en" | "hi"


@router.post("/command")
async def handle_command(req: CommandRequest):
    # ── 1. Resolve text ────────────────────────────────────────────────────────
    text = req.text

    if not text and req.audio_base64:
        # Decode base64 audio → transcribe via Groq Whisper
        try:
            audio_bytes = base64.b64decode(req.audio_base64)
            # Groq Whisper expects a file-like object; use httpx multipart
            import httpx, tempfile
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as f:
                transcription = await groq_client.audio.transcriptions.create(
                    file=("audio.webm", f, "audio/webm"),
                    model="whisper-large-v3",
                    language=None,  # auto-detect
                    response_format="text",
                )
            text = str(transcription).strip()
            import os as _os; _os.unlink(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Whisper transcription failed: {e}")

    if not text:
        raise HTTPException(status_code=400, detail="Either 'text' or 'audio_base64' is required.")

    # ── 2. Parse intent ────────────────────────────────────────────────────────
    intent_data = await parse_intent(text, req.response_language)
    intent = intent_data.get("intent", "unknown")
    item_name = intent_data.get("item")
    category = intent_data.get("category", "other")
    quantity = intent_data.get("quantity", 1)
    unit = intent_data.get("unit", "")
    detected_lang = intent_data.get("detected_language", "en")

    pool = await get_pool()

    # ── 3. Route intent to handler ─────────────────────────────────────────────
    if intent == "add_item" and item_name:
        async with pool.acquire() as conn:
            # Upsert: if item already active, increase quantity
            existing = await conn.fetchrow(
                "SELECT id, quantity FROM items WHERE session_id=$1 AND LOWER(name)=$2 AND status='active'",
                req.session_id, item_name.lower(),
            )
            if existing:
                await conn.execute(
                    "UPDATE items SET quantity=quantity+$1 WHERE id=$2",
                    quantity, existing["id"],
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO items(session_id, name, category, quantity, unit)
                    VALUES($1, $2, $3, $4, $5)
                    """,
                    req.session_id, item_name, category, quantity, unit,
                )
            await conn.execute(
                "INSERT INTO history(session_id, item_name, category, event) VALUES($1,$2,$3,'added')",
                req.session_id, item_name, category,
            )

    elif intent == "remove_item" and item_name:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM items WHERE session_id=$1 AND LOWER(name)=$2",
                req.session_id, item_name.lower(),
            )
            await conn.execute(
                "INSERT INTO history(session_id, item_name, category, event) VALUES($1,$2,$3,'removed')",
                req.session_id, item_name, category,
            )

    elif intent == "mark_purchased" and item_name:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE items SET status='purchased' WHERE session_id=$1 AND LOWER(name)=$2",
                req.session_id, item_name.lower(),
            )
            await conn.execute(
                "INSERT INTO history(session_id, item_name, category, event) VALUES($1,$2,$3,'purchased')",
                req.session_id, item_name, category,
            )

    # ── 4. Fetch updated list ──────────────────────────────────────────────────
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, category, quantity, unit, status
            FROM items
            WHERE session_id=$1 AND status='active'
            ORDER BY category, name
            """,
            req.session_id,
        )

    grouped: dict[str, list] = {}
    for row in rows:
        cat = row["category"] or "other"
        grouped.setdefault(cat, [])
        grouped[cat].append({
            "id": str(row["id"]),
            "name": row["name"],
            "quantity": row["quantity"],
            "unit": row["unit"],
        })

    # ── 5. Attach substitutes if applicable ───────────────────────────────────
    substitutes: list[str] = []
    if intent == "suggest_substitute" and item_name:
        key = item_name.lower()
        substitutes = SUBSTITUTES.get(key, [])
        # Also check partial match
        if not substitutes:
            for k, v in SUBSTITUTES.items():
                if k in key or key in k:
                    substitutes = v
                    break

    # ── 6. Suggestions from history ────────────────────────────────────────────
    async with pool.acquire() as conn:
        active_names_rows = await conn.fetch(
            "SELECT LOWER(name) as name FROM items WHERE session_id=$1 AND status='active'",
            req.session_id,
        )
        active_names = {r["name"] for r in active_names_rows}

        hist_rows = await conn.fetch(
            """
            SELECT item_name, category, COUNT(*) as freq
            FROM history
            WHERE session_id=$1 AND event IN ('added','purchased')
            GROUP BY item_name, category
            HAVING COUNT(*) >= 2
            ORDER BY freq DESC LIMIT 5
            """,
            req.session_id,
        )

    suggestions = [
        {"name": r["item_name"], "category": r["category"]}
        for r in hist_rows
        if r["item_name"].lower() not in active_names
    ]

    confirmation = build_confirmation(intent_data, req.response_language)

    return {
        "transcript": text,
        "intent": intent_data,
        "confirmation": confirmation,
        "detected_language": detected_lang,
        "list": grouped,
        "substitutes": substitutes,
        "suggestions": suggestions,
    }
