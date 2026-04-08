import os
import ssl
import asyncpg
import structlog

log = structlog.get_logger()
_pool = None


async def get_pool():
    global _pool
    if _pool is not None:
        return _pool

    database = os.getenv("ALLOYDB_DATABASE", "aria")
    user = os.getenv("ALLOYDB_USER", "aadarsh_praveen")
    password = os.getenv("ALLOYDB_PASSWORD", "")
    host = os.getenv("ALLOYDB_HOST", "localhost")
    port = int(os.getenv("ALLOYDB_PORT", "5432"))
    cloud_run = os.getenv("K_SERVICE")

    # Use SSL when connecting to AlloyDB (both local and Cloud Run)
    use_ssl = host != "localhost" and host != "127.0.0.1"

    if use_ssl:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    else:
        ssl_context = False

    log.info("Connecting to database", host=host, cloud_run=bool(cloud_run), ssl=use_ssl)

    try:
        if password:
            dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        else:
            dsn = f"postgresql://{user}@{host}:{port}/{database}"

        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=10,
            ssl=ssl_context
        )
        log.info("✅ AlloyDB connection pool created")
    except Exception as e:
        log.error("Database connection failed", error=str(e))
        raise

    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log.info("AlloyDB pool closed")


async def execute(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def fetch_val(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)