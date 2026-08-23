from fastapi import APIRouter, HTTPException
from db import get_pool

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/list")
async def get_list(session_id: str):
    """Return active items grouped by category for a session."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, category, quantity, unit, status, created_at
            FROM items
            WHERE session_id = $1 AND status = 'active'
            ORDER BY category, created_at
            """,
            session_id,
        )

    # Group by category
    grouped: dict[str, list] = {}
    for row in rows:
        cat = row["category"] or "other"
        grouped.setdefault(cat, [])
        grouped[cat].append(
            {
                "id": str(row["id"]),
                "name": row["name"],
                "quantity": row["quantity"],
                "unit": row["unit"],
                "status": row["status"],
            }
        )

    return {"categories": grouped, "total": len(rows)}


@router.delete("/{item_id}")
async def delete_item(item_id: str, session_id: str):
    """Remove an item by id (voice misfire safety net)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT name, category FROM items WHERE id=$1 AND session_id=$2",
            item_id,
            session_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")

        await conn.execute(
            "DELETE FROM items WHERE id=$1", item_id
        )
        # Log to history
        await conn.execute(
            """
            INSERT INTO history(session_id, item_name, category, event)
            VALUES($1, $2, $3, 'removed')
            """,
            session_id,
            row["name"],
            row["category"],
        )

    return {"deleted": item_id, "item": row["name"]}
