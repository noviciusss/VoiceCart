import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=os.environ["DATABASE_URL"],
            min_size=1,
            max_size=5,
        )
        await _run_migrations(_pool)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def _run_migrations(pool: asyncpg.Pool):
    """Run schema.sql to ensure tables exist."""
    schema_path = Path(__file__).parent / "schema.sql"
    sql = schema_path.read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)
