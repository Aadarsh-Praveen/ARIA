import asyncpg
import structlog
from contextlib import asynccontextmanager
from config import settings

log = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            database=settings.alloydb_database,
            user="aadarsh_praveen",
            password="",
            min_size=2,
            max_size=10,
            command_timeout=60,
            ssl=False,          # ← add this
        )
        log.info("✅ AlloyDB connection pool created")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log.info("AlloyDB pool closed")


@asynccontextmanager
async def get_connection():
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection


async def execute(query: str, *args):
    async with get_connection() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args) -> dict | None:
    async with get_connection() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> list[dict]:
    async with get_connection() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def fetch_val(query: str, *args):
    async with get_connection() as conn:
        return await conn.fetchval(query, *args)