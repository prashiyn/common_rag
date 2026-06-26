from fastapi import APIRouter, HTTPException

from app import db_config
from app.rag_cache import get_rag, _rag_cache
from app.workspace_config import WorkspaceConfigPayload, merge_workspace_config

router = APIRouter(tags=["config"])

@router.get("/config", tags=["config"])
async def config_endpoint():
    """Return non-secret app config (storage types, default workspace, parser)."""
    return {
        "working_dir": WORKING_DIR,
        "workspace_default": WORKSPACE_DEFAULT,
        "parser": PARSER,
        "parse_method": PARSE_METHOD,
        "llm_service_base_url": LLM_SERVICE_BASE_URL,
        "llm_service_llm_provider": LLM_SERVICE_LLM_PROVIDER,
        "lightrag_kv_storage": LIGHTRAG_KV_STORAGE,
        "lightrag_vector_storage": LIGHTRAG_VECTOR_STORAGE,
        "lightrag_graph_storage": LIGHTRAG_GRAPH_STORAGE,
        "lightrag_doc_status_storage": LIGHTRAG_DOC_STATUS_STORAGE,
    }


@router.get("/config/{workspace_id}", tags=["config"])
async def get_workspace_config(workspace_id: str):
    """Get config stored for the given workspace (from DB). 404 if not set."""
    cfg = await db_config.get_config(workspace_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"No config for workspace {workspace_id!r}")
    return cfg


@router.post("/config/{workspace_id}", tags=["config"])
async def set_workspace_config(workspace_id: str, config: WorkspaceConfigPayload):
    """
    Set config for workspace. Payload is partial; missing keys are filled from env defaults.
    Only known keys are allowed (validation error for unknown keys). Stored in DB and _rag_cache updated.
    """
    if db_config._pool is None:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL not configured; set POSTGRES_HOST, POSTGRES_DATABASE, etc.",
        )
    payload = config.model_dump(exclude_none=True)
    full_config = merge_workspace_config(workspace_id, payload)
    await db_config.set_config(workspace_id, full_config)
    if workspace_id in _rag_cache:
        del _rag_cache[workspace_id]
    await get_rag(workspace_id)
    return {"status": "ok", "workspace_id": workspace_id}


