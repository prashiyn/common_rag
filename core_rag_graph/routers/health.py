from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness probe endpoint."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready():
    """Readiness probe endpoint."""
    return {"status": "ready"}
