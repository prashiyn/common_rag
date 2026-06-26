from contextlib import asynccontextmanager

from fastapi import FastAPI

from llm_service.config import apply_litellm_env, get_settings
from llm_service.logging_setup import configure_litellm_debug, configure_logging
from llm_service.routers import health, llm, openai


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    verbose = settings.debug or settings.litellm_debug
    configure_logging(debug=verbose)
    configure_litellm_debug(enabled=verbose)
    apply_litellm_env(settings)
    app = FastAPI(
        title=settings.app_name,
        description="Standalone LLM gateway service.",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(llm.router, prefix="/llm", tags=["llm"])
    app.include_router(openai.router, prefix="/v1", tags=["openai"])
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("llm_service.main:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    run()
