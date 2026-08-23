from fastapi import APIRouter
from db import get_pool

router = APIRouter(prefix="/suggestions", tags=["suggestions"])

# Minimum frequency to surface a suggestion
MIN_FREQUENCY = 2


@router.get("")
async def get_suggestions(session_id: str):
    """
    Return items the user has historically bought (freq >= 2)
    that are NOT currently in their active list.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Items currently in active list
        active = await conn.fetch(
            "SELECT LOWER(name) as name FROM items WHERE session_id=$1 AND status='active'",
            session_id,
        )
        active_names = {row["name"] for row in active}

        # Historical items by frequency
        rows = await conn.fetch(
            """
            SELECT item_name, category, COUNT(*) as freq
            FROM history
            WHERE session_id=$1 AND event IN ('added', 'purchased')
            GROUP BY item_name, category
            HAVING COUNT(*) >= $2
            ORDER BY freq DESC
            LIMIT 8
            """,
            session_id,
            MIN_FREQUENCY,
        )

    suggestions = [
        {"name": row["item_name"], "category": row["category"], "frequency": row["freq"]}
        for row in rows
        if row["item_name"].lower() not in active_names
    ]

    return {"suggestions": suggestions}
