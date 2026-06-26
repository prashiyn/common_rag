from fastapi import APIRouter

from app.rag_cache import get_rag
from app.schemas import QueryRequest, QueryResponse, QueryMultimodalRequest

router = APIRouter(tags=["query"])

@router.post("/query", response_model=QueryResponse, tags=["query"])
async def query(req: QueryRequest):
    """Text query over the indexed knowledge base for the given workspace."""
    rag = await get_rag(req.workspace)
    await rag._ensure_lightrag_initialized()
    kwargs = {}
    if req.system_prompt is not None:
        kwargs["system_prompt"] = req.system_prompt
    if req.vlm_enhanced is not None:
        kwargs["vlm_enhanced"] = req.vlm_enhanced
    answer = await rag.aquery(req.query, mode=req.mode, **kwargs)
    return QueryResponse(answer=answer)


@router.post("/query/multimodal", response_model=QueryResponse, tags=["query"])
async def query_multimodal(req: QueryMultimodalRequest):
    """Query with inline multimodal content (tables, equations, image paths)."""
    rag = await get_rag(req.workspace)
    await rag._ensure_lightrag_initialized()
    raw = [item.model_dump(exclude_none=True) for item in req.multimodal_content]
    answer = await rag.aquery_with_multimodal(req.query, multimodal_content=raw, mode=req.mode)
    return QueryResponse(answer=answer)


