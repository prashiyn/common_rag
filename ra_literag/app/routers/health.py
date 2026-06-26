from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.config import LLM_SERVICE_BASE_URL

router = APIRouter(tags=["health"])


@router.get("/health", response_class=PlainTextResponse, tags=["health"])
async def health():
    """Liveness: always 200. Use /ready for readiness."""
    return "ok"


@router.get("/ready", response_class=PlainTextResponse, tags=["health"])
async def ready():
    """Readiness: 200 if doc-processing endpoint is configured."""
    if not LLM_SERVICE_BASE_URL:
        raise HTTPException(status_code=503, detail="LLM_SERVICE_BASE_URL not set")
    return "ready"


