"""
PostgreSQL-backed workspace config for ra_litelag.
Table: ra_litelag_config (workspace_id, config JSONB, created_at, updated_at).
"""

from __future__ import annotations

import os
from typing import Any

import asyncpg

TABLE_NAME = "ra_litelag_config"
_pool: asyncpg.Pool | None = None


def _conn_info() -> dict[str, Any]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", ""),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "database": os.getenv("POSTGRES_DATABASE", ""),
    }


async def init_pool() -> None:
    """Create connection pool. Idempotent. No-op if POSTGRES_DATABASE not set."""
    global _pool
    if _pool is not None:
        return
    info = _conn_info()
    if not info.get("database"):
        return
    _pool = await asyncpg.create_pool(
        host=info["host"],
        port=info["port"],
        user=info["user"],
        password=info["password"],
        database=info["database"],
        min_size=1,
        max_size=4,
        command_timeout=10,
    )
    await ensure_table()


async def close_pool() -> None:
    """Close pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def ensure_table() -> None:
    """Create ra_litelag_config table if not exists."""
    if _pool is None:
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                workspace_id TEXT PRIMARY KEY,
                config JSONB NOT NULL DEFAULT '{{}}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


async def get_config(workspace_id: str) -> dict[str, Any] | None:
    """Return config for workspace, or None if not found."""
    if _pool is None:
        return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT config FROM {TABLE_NAME} WHERE workspace_id = $1",
            workspace_id,
        )
        return dict(row["config"]) if row else None


async def set_config(workspace_id: str, config: dict[str, Any]) -> None:
    """Upsert config for workspace."""
    if _pool is None:
        raise RuntimeError("PostgreSQL pool not initialized; set POSTGRES_* env.")
    async with _pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (workspace_id, config, created_at, updated_at)
            VALUES ($1, $2::jsonb, NOW(), NOW())
            ON CONFLICT (workspace_id) DO UPDATE SET
                config = EXCLUDED.config,
                updated_at = NOW()
            """,
            workspace_id,
            asyncpg.types.Json(config),
        )


async def list_workspace_ids() -> list[str]:
    """Return all workspace_ids in the table."""
    if _pool is None:
        return []
    async with _pool.acquire() as conn:
        rows = await conn.fetch(f"SELECT workspace_id FROM {TABLE_NAME}")
        return [r["workspace_id"] for r in rows]
