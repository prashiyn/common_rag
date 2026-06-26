from __future__ import annotations

from fastapi import HTTPException, Request
from neo4j.exceptions import Neo4jError

from temporial_graph_rag.api.dependencies import require_neo4j_store
from temporial_graph_rag.models.query import EntityCollectionConnection, EntityCollectionsResponse

from fastapi import APIRouter

router = APIRouter()

@router.get("/v1/network/entities/{entity_name}/collections", response_model=EntityCollectionsResponse)
async def entity_collections_network(
    request: Request,
    entity_name: str,
    limit: int = 25,
) -> EntityCollectionsResponse:
    store = require_neo4j_store(request)
    limit = min(max(limit, 1), 100)
    try:
        rows = store.entity_collection_connections(entity_name=entity_name, limit=limit)
    except Neo4jError as exc:
        raise HTTPException(status_code=502, detail=f"Neo4j query failed: {exc}") from exc
    return EntityCollectionsResponse(
        entity_name=entity_name,
        connections=[EntityCollectionConnection(**r) for r in rows],
    )


