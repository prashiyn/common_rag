from fastapi import APIRouter

from raqe.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
