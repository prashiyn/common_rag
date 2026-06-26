from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from temporial_graph_rag.api.collection_name_middleware import CollectionNameExposeMiddleware
from temporial_graph_rag.api.constants import REPO_ROOT
from temporial_graph_rag.api.registry_holder import registry
from temporial_graph_rag.api.routers import collections, health, ingest, network, search
from temporial_graph_rag.collections.registry import CollectionRegistry, Neo4jCollectionRegistry
from temporial_graph_rag.graph import Neo4jGraphStore, Neo4jSettings
from temporial_graph_rag.llm import LLMClient, LLMServiceConfig

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(REPO_ROOT / ".env")
    neo4j_settings = Neo4jSettings.from_env()
    if neo4j_settings.enabled:
        store = Neo4jGraphStore(neo4j_settings)
        app.state.neo4j_store = store
        registry.set_backend(Neo4jCollectionRegistry(store))
    else:
        app.state.neo4j_store = None
        registry.set_backend(CollectionRegistry())

    if os.getenv("LLM_STARTUP_MODELS_CHECK", "").strip().lower() in ("1", "true", "yes", "on"):
        try:
            cfg = LLMServiceConfig.from_env()
            llm_probe = LLMClient(cfg)
            try:
                llm_probe.models()
            finally:
                llm_probe.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM_STARTUP_MODELS_CHECK: GET /llm/models failed: %s", exc)

    yield
    store = getattr(app.state, "neo4j_store", None)
    if store is not None:
        store.close()


app = FastAPI(title="temporial-graph-rag", lifespan=lifespan)
app.add_middleware(CollectionNameExposeMiddleware)

app.include_router(health.router)
app.include_router(collections.router)
app.include_router(search.router)
app.include_router(network.router)
app.include_router(ingest.router)
