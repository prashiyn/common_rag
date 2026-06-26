import os
from typing import Dict

from fastapi import WebSocket

from graph.config import get_config
from graph.utils.logger import logger
from graph.utils.graph_repository import (
    NetworkXJsonGraphRepository,
    Neo4jGraphRepository,
    DualWriteGraphRepository,
    GraphRepository,
)

CONFIG = get_config()
RUNTIME_METRICS = {
    "ingest_latency_ms_total": 0.0,
    "ingest_requests_total": 0,
    "query_latency_ms_total": 0.0,
    "query_requests_total": 0,
}


def _create_graph_repository() -> GraphRepository:
    def _build_single_backend(name: str) -> GraphRepository:
        backend = name.strip().lower()
        if backend == "neo4j":
            uri = os.getenv("NEO4J_URI", "").strip()
            user = os.getenv("NEO4J_USER", "").strip()
            password = os.getenv("NEO4J_PASSWORD", "").strip()
            database = os.getenv("NEO4J_DATABASE", "neo4j").strip()
            if not uri or not user or not password:
                raise RuntimeError(
                    "neo4j backend requires NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD"
                )
            return Neo4jGraphRepository(uri=uri, user=user, password=password, database=database)
        if backend == "networkx":
            return NetworkXJsonGraphRepository()
        raise RuntimeError(f"Unsupported GRAPH_BACKEND: {name}")

    primary_name = os.getenv("GRAPH_BACKEND", "networkx")
    primary = _build_single_backend(primary_name)

    dual_write = os.getenv("GRAPH_DUAL_WRITE", "false").strip().lower() in ("1", "true", "yes")
    if not dual_write:
        logger.info(f"Graph repository backend: {primary_name.strip().lower()}")
        return primary

    secondary_name = os.getenv("GRAPH_SECONDARY_BACKEND", "networkx").strip().lower()
    if secondary_name == primary_name.strip().lower():
        raise RuntimeError("GRAPH_SECONDARY_BACKEND must differ from GRAPH_BACKEND when GRAPH_DUAL_WRITE=true")
    secondary = _build_single_backend(secondary_name)
    strict = os.getenv("GRAPH_DUAL_WRITE_STRICT", "true").strip().lower() in ("1", "true", "yes")
    logger.info(
        "Graph repository dual-write enabled: "
        f"primary={primary_name.strip().lower()}, secondary={secondary_name}, strict={strict}"
    )
    return DualWriteGraphRepository(primary=primary, secondary=secondary, check_consistency=strict)



GRAPH_REPOSITORY: GraphRepository = _create_graph_repository()

active_connections: Dict[str, WebSocket] = {}
