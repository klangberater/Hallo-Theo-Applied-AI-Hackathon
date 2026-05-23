"""Async Postgres connection pool for the theo schema.

Single source of database access. Every connection runs
`SET search_path TO theo, public` so the agent's L2 tools see theo
tables first.

See: docs/PRODUCT_SPEC.md §2.4
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import asyncpg
from dotenv import load_dotenv

# Load /opt/fletcher/.env on the server, or .env locally for dev.
_ENV_CANDIDATES = [
    Path("/opt/fletcher/.env"),
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path.cwd() / ".env",
]
for _candidate in _ENV_CANDIDATES:
    if _candidate.exists():
        load_dotenv(_candidate)
        break

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Expected in /opt/fletcher/.env or local .env."
    )


_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Run on every fresh connection. Pins the search_path."""
    await conn.execute("SET search_path TO theo, public")


async def get_pool() -> asyncpg.Pool:
    """Lazy-initialize the global pool. Call from app startup."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            init=_init_connection,
            command_timeout=30,
        )
    return _pool


@asynccontextmanager
async def connect() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection from the pool for the lifetime of the with-block."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def close_pool() -> None:
    """Close the pool. Call from app shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
