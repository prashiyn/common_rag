"""Unified lifespan — startup and shutdown for all merged services."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def _startup_llm_service(app: FastAPI) -> None:
    try:
        from llm_service.config import apply_litellm_env, get_settings as llm_get_settings
        from llm_service.logging_setup import configure_litellm_debug, configure_logging

        settings = llm_get_settings()
        verbose = settings.debug or settings.litellm_debug
        configure_logging(debug=verbose)
        configure_litellm_debug(enabled=verbose)
        apply_litellm_env(settings)
        logger.info("[llm-service] startup complete")
    except Exception as exc:
        logger.warning("[llm-service] startup failed (non-fatal): %s", exc)


def _startup_doc_processing(app: FastAPI) -> None:
    try:
        from doc_processing.debug_trace import configure_debug_logging

        configure_debug_logging()
        logger.info("[doc_processing] startup complete")
    except Exception as exc:
        logger.warning("[doc_processing] startup failed (non-fatal): %s", exc)


def _startup_core_rag_graph(app: FastAPI) -> None:
    try:
        from state import GRAPH_REPOSITORY

        app.state.crg_graph_repository = GRAPH_REPOSITORY
        logger.info(
            "[core_rag_graph] startup complete (backend=%s)",
            type(GRAPH_REPOSITORY).__name__,
        )
    except Exception as exc:
        logger.warning("[core_rag_graph] startup failed (non-fatal): %s", exc)


def _shutdown_core_rag_graph(app: FastAPI) -> None:
    repo = getattr(app.state, "crg_graph_repository", None)
    if repo is not None:
        try:
            close_fn = getattr(repo, "close", None)
            if callable(close_fn):
                close_fn()
            logger.info("[core_rag_graph] shutdown complete")
        except Exception as exc:
            logger.warning("[core_rag_graph] shutdown error: %s", exc)


def _startup_temporial_graph(app: FastAPI) -> None:
    try:
        from pathlib import Path

        from dotenv import load_dotenv
        from temporial_graph_rag.api.registry_holder import registry
        from temporial_graph_rag.collections.registry import CollectionRegistry, Neo4jCollectionRegistry
        from temporial_graph_rag.graph import Neo4jGraphStore, Neo4jSettings
        from temporial_graph_rag.llm import LLMClient, LLMServiceConfig

        repo_root = Path(__file__).resolve().parents[1]
        load_dotenv(repo_root / ".env")
        neo4j_settings = Neo4jSettings.from_env()
        if neo4j_settings.enabled:
            store = Neo4jGraphStore(neo4j_settings)
            app.state.tg_neo4j_store = store
            registry.set_backend(Neo4jCollectionRegistry(store))
        else:
            app.state.tg_neo4j_store = None
            registry.set_backend(CollectionRegistry())

        if os.getenv("LLM_STARTUP_MODELS_CHECK", "").strip().lower() in ("1", "true", "yes", "on"):
            try:
                cfg = LLMServiceConfig.from_env()
                probe = LLMClient(cfg)
                try:
                    probe.models()
                finally:
                    probe.close()
            except Exception as probe_exc:
                logger.warning("[temporial_graph] LLM probe failed: %s", probe_exc)

        logger.info("[temporial_graph] startup complete")
    except Exception as exc:
        logger.warning("[temporial_graph] startup failed (non-fatal): %s", exc)


def _shutdown_temporial_graph(app: FastAPI) -> None:
    store = getattr(app.state, "tg_neo4j_store", None)
    if store is not None:
        try:
            store.close()
            logger.info("[temporial_graph] shutdown complete")
        except Exception as exc:
            logger.warning("[temporial_graph] shutdown error: %s", exc)


async def _startup_temporial_graph_openai(app: FastAPI) -> None:
    try:
        from temporal_graph.jobs.manager import JobManager, ingest_worker_loop
        from temporal_graph.neo4j.bootstrap import bootstrap_graph
        from temporal_graph.neo4j.driver import get_driver
        from temporal_graph.settings import get_settings as tgo_get_settings

        settings = tgo_get_settings()
        app.state.tgo_settings = settings
        app.state.tgo_job_manager = JobManager(settings)
        app.state.tgo_worker_stop = asyncio.Event()
        app.state.tgo_worker_task = None

        if (
            (settings.job_backend or "").strip().lower() == "redis"
            and settings.ingest_start_redis_worker
            and settings.redis_url
        ):
            app.state.tgo_worker_task = asyncio.create_task(
                ingest_worker_loop(app, app.state.tgo_worker_stop)
            )
            logger.info("[temporial_graph_openai] Redis ingest worker started")

        driver = get_driver(settings)
        app.state.tgo_neo4j_driver = driver
        try:
            await bootstrap_graph(driver, settings)
        except Exception as bootstrap_exc:
            logger.warning("[temporial_graph_openai] Neo4j bootstrap failed: %s", bootstrap_exc)

        logger.info("[temporial_graph_openai] startup complete")
    except Exception as exc:
        logger.warning("[temporial_graph_openai] startup failed (non-fatal): %s", exc)


async def _shutdown_temporial_graph_openai(app: FastAPI) -> None:
    worker_stop = getattr(app.state, "tgo_worker_stop", None)
    if worker_stop is not None:
        worker_stop.set()
    worker_task = getattr(app.state, "tgo_worker_task", None)
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    job_manager = getattr(app.state, "tgo_job_manager", None)
    if job_manager is not None:
        try:
            await job_manager.aclose()
        except Exception:
            pass
    driver = getattr(app.state, "tgo_neo4j_driver", None)
    if driver is not None:
        try:
            from temporal_graph.neo4j.driver import close_driver

            await close_driver()
        except Exception as exc:
            logger.warning("[temporial_graph_openai] Neo4j driver close error: %s", exc)
    logger.info("[temporial_graph_openai] shutdown complete")


async def _startup_ra_literag(app: FastAPI) -> None:
    try:
        from app import db_config as ra_db_config
        from app.rag_cache import get_rag

        await ra_db_config.init_pool()
        for workspace_id in await ra_db_config.list_workspace_ids():
            try:
                await get_rag(workspace_id)
            except Exception:
                pass
        app.state.ra_literag_db_config = ra_db_config
        logger.info("[ra_literag] startup complete")
    except Exception as exc:
        logger.warning("[ra_literag] startup failed (non-fatal): %s", exc)


async def _shutdown_ra_literag(app: FastAPI) -> None:
    try:
        from app import db_config as ra_db_config
        from app.rag_cache import _rag_cache

        for rag in list(_rag_cache.values()):
            try:
                await rag.finalize_storages()
            except Exception:
                pass
        _rag_cache.clear()
        await ra_db_config.close_pool()
        logger.info("[ra_literag] shutdown complete")
    except Exception as exc:
        logger.warning("[ra_literag] shutdown error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _startup_llm_service(app)
    _startup_doc_processing(app)
    _startup_core_rag_graph(app)
    _startup_temporial_graph(app)
    await _startup_temporial_graph_openai(app)
    await _startup_ra_literag(app)

    logger.info("unified-api startup complete")
    yield

    await _shutdown_ra_literag(app)
    await _shutdown_temporial_graph_openai(app)
    _shutdown_temporial_graph(app)
    _shutdown_core_rag_graph(app)
    logger.info("unified-api shutdown complete")
