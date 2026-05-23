"""Async Postgres connection pool for the theo schema.

Single source of database access. Every connection runs
`SET search_path TO theo, public` so the agent's L2 tools see theo
tables first.

See: docs/PRODUCT_SPEC.md §2.4
"""
from __future__ import annotations

import json
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


def _json_encoder(value):
    """Lenient encoder — accepts either a JSON-string (pre-serialized) or a
    Python object. Necessary because much of the codebase calls json.dumps()
    itself before passing the value as $N::jsonb. With the default
    json.dumps encoder, those values would be double-encoded into a JSONB
    string value (top-level "string" instead of "object")."""
    if isinstance(value, (str, bytes, bytearray)):
        return value  # already serialized — pass through
    return json.dumps(value, default=str, ensure_ascii=False)


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Run on every fresh connection: pin search_path + auto-decode JSON(B).

    Without these codecs, asyncpg returns jsonb columns as raw strings
    (psycopg2 does the decode for free, hence why the Streamlit path worked
    without them). The FastAPI/Next.js path consumes the FastAPI response
    directly, so unconverted strings break clients that expect objects.
    """
    await conn.execute("SET search_path TO theo, public")
    await conn.set_type_codec(
        "jsonb",
        encoder=_json_encoder,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=_json_encoder,
        decoder=json.loads,
        schema="pg_catalog",
    )


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
