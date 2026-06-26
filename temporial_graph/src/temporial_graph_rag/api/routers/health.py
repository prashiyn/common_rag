from __future__ import annotations

from fastapi import Depends, Request

from temporial_graph_rag.api.dependencies import get_llm_client, get_neo4j_store
from temporial_graph_rag.llm import LLMClient

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/health/llm")
async def llm_health(llm: LLMClient = Depends(get_llm_client)) -> dict[str, object]:
    """Diagnostic: reachability of llm-service ``GET /llm/models`` (plan §8.2)."""
    try:
        payload = llm.models()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {exc}") from exc
    return {"llm": "ok", "models_response": payload}


@router.get("/v1/health/neo4j")
async def neo4j_health(request: Request) -> dict[str, str]:
    store = get_neo4j_store(request)
    if store is None:
        return {"neo4j": "disabled"}
    try:
        store.ping()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {exc}") from exc
    return {"neo4j": "ok"}


