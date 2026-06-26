"""Unified FastAPI application — all merged services in one process."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from unified_api.lifespan import lifespan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Unified API",
    description=(
        "All services in one process: llm-service, doc-processing, core-rag-graph, "
        "ra-literag, temporal-graph, temporal-graph-openai, temporal-graph-traversal."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def unified_health():
    return {"status": "ok", "service": "unified-api"}


# --- llm-service ---
try:
    from llm_service.routers import health as llm_health, llm as llm_llm, openai as llm_openai

    app.include_router(llm_health.router, prefix="/llm-service/health", tags=["llm-service"])
    app.include_router(llm_llm.router, prefix="/llm-service/llm", tags=["llm-service"])
    app.include_router(llm_openai.router, prefix="/llm-service/v1", tags=["llm-service"])
    logger.info("Mounted llm-service at /llm-service")
except ImportError as exc:
    logger.error("Failed to mount llm-service: %s", exc)


# --- doc_processing ---
try:
    from doc_processing.routers import documents as dp_documents, health as dp_health

    app.include_router(dp_health.router, prefix="/doc-processing/health", tags=["doc-processing"])
    app.include_router(dp_documents.router, prefix="/doc-processing/documents", tags=["doc-processing"])
    logger.info("Mounted doc_processing at /doc-processing")
except ImportError as exc:
    logger.error("Failed to mount doc_processing: %s", exc)


# --- core_rag_graph ---
try:
    from graph.utils.collection_id_middleware import CollectionIdMiddleware
    from routers.graph_api import router as crg_graph_api_router
    from routers.health import router as crg_health_router

    app.add_middleware(CollectionIdMiddleware)
    app.include_router(crg_health_router, prefix="/core-rag", tags=["core-rag"])
    app.include_router(crg_graph_api_router, prefix="/core-rag", tags=["core-rag"])
    logger.info("Mounted core_rag_graph at /core-rag")
except ImportError as exc:
    logger.error("Failed to mount core_rag_graph: %s", exc)


# --- ra_literag ---
try:
    from app.routers.config import router as ral_config_router
    from app.routers.health import router as ral_health_router
    from app.routers.ingest import router as ral_ingest_router
    from app.routers.query import router as ral_query_router

    app.include_router(ral_health_router, prefix="/ra-literag", tags=["ra-literag"])
    app.include_router(ral_config_router, prefix="/ra-literag", tags=["ra-literag"])
    app.include_router(ral_query_router, prefix="/ra-literag", tags=["ra-literag"])
    app.include_router(ral_ingest_router, prefix="/ra-literag", tags=["ra-literag"])
    logger.info("Mounted ra_literag at /ra-literag")
except ImportError as exc:
    logger.error("Failed to mount ra_literag: %s", exc)


# --- temporial_graph ---
try:
    from temporial_graph_rag.api.collection_name_middleware import CollectionNameExposeMiddleware
    from temporial_graph_rag.api.routers import (
        collections as tg_collections,
        health as tg_health,
        ingest as tg_ingest,
        network as tg_network,
        search as tg_search,
    )

    app.add_middleware(CollectionNameExposeMiddleware)
    app.include_router(tg_health.router, prefix="/temporal-graph", tags=["temporal-graph"])
    app.include_router(tg_collections.router, prefix="/temporal-graph", tags=["temporal-graph"])
    app.include_router(tg_search.router, prefix="/temporal-graph", tags=["temporal-graph"])
    app.include_router(tg_network.router, prefix="/temporal-graph", tags=["temporal-graph"])
    app.include_router(tg_ingest.router, prefix="/temporal-graph", tags=["temporal-graph"])
    logger.info("Mounted temporial_graph at /temporal-graph")
except ImportError as exc:
    logger.error("Failed to mount temporial_graph: %s", exc)


# --- temporial_graph_openai ---
try:
    from temporal_graph.api.collection_routes import router as tgo_collection_router
    from temporal_graph.api.health_routes import router as tgo_health_router
    from temporal_graph.api.ingest_routes import router as tgo_ingest_router
    from temporal_graph.api.retrieve_routes import router as tgo_retrieve_router
    from temporal_graph.middleware.collection_wire import (
        CollectionPathRewriteMiddleware,
        CollectionWireResponseMiddleware,
    )

    app.add_middleware(CollectionWireResponseMiddleware)
    app.add_middleware(CollectionPathRewriteMiddleware)
    app.include_router(tgo_health_router, prefix="/temporal-graph-openai", tags=["temporal-graph-openai"])
    app.include_router(tgo_ingest_router, prefix="/temporal-graph-openai", tags=["temporal-graph-openai"])
    app.include_router(tgo_retrieve_router, prefix="/temporal-graph-openai", tags=["temporal-graph-openai"])
    app.include_router(tgo_collection_router, prefix="/temporal-graph-openai", tags=["temporal-graph-openai"])
    logger.info("Mounted temporial_graph_openai at /temporal-graph-openai")
except ImportError as exc:
    logger.error("Failed to mount temporial_graph_openai: %s", exc)


# --- temporial_graph_traversal (raqe package) ---
try:
    from raqe.api.collection_routes import router as raqe_collection_router
    from raqe.api.health_routes import router as raqe_health_router
    from raqe.api.query_routes import router as raqe_query_router
    from raqe.middleware.collection_namespace import CollectionNamespaceMiddleware

    app.add_middleware(CollectionNamespaceMiddleware)
    app.include_router(raqe_health_router, prefix="/temporal-graph-traversal", tags=["temporal-graph-traversal"])
    app.include_router(raqe_query_router, prefix="/temporal-graph-traversal", tags=["temporal-graph-traversal"])
    app.include_router(raqe_collection_router, prefix="/temporal-graph-traversal", tags=["temporal-graph-traversal"])
    logger.info("Mounted temporial_graph_traversal at /temporal-graph-traversal")
except ImportError as exc:
    logger.error("Failed to mount temporial_graph_traversal: %s", exc)


def run() -> None:
    import uvicorn

    uvicorn.run("unified_api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
