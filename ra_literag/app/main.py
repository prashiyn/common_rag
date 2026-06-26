"""
RAG-Anything FastAPI service.

Exposes RAG-Anything (multimodal RAG) as HTTP API: query, process documents, insert content.
Multi-tenant: pass workspace (tenant id) on every request; data is isolated by LightRAG workspace.
Configure via .env (see env.example). Use `uv run` to run with server deps.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app import db_config
from app.config import WORKSPACE_DEFAULT
from app.rag_cache import _rag_cache, get_rag
from app.routers.config import router as config_router
from app.routers.health import router as health_router
from app.routers.ingest import router as ingest_router
from app.routers.query import router as query_router

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init Postgres pool, ensure table, load workspace configs from DB into _rag_cache. Shutdown: close pool, finalize RAGs."""
    try:
        await db_config.init_pool()
        for workspace_id in await db_config.list_workspace_ids():
            try:
                await get_rag(workspace_id)
            except Exception:
                pass
    except Exception:
        pass
    yield
    for rag in list(_rag_cache.values()):
        try:
            await rag.finalize_storages()
        except Exception:
            pass
    _rag_cache.clear()
    await db_config.close_pool()


app = FastAPI(
    title="RAG-Anything API",
    description="Multimodal RAG service: query, process documents, insert content. Multi-tenant via workspace parameter.",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Liveness and readiness probes"},
        {"name": "config", "description": "App and per-workspace config (GET/POST)"},
        {"name": "query", "description": "Text and multimodal RAG queries"},
        {"name": "ingest", "description": "Content insert and document processing"},
    ],
    servers=[{"url": "/", "description": "Default (relative to base URL)"}],
)

app.include_router(health_router)
app.include_router(config_router)
app.include_router(query_router)
app.include_router(ingest_router)


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
