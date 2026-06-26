from fastapi import FastAPI

from raqe.api.collection_routes import router as collection_router
from raqe.api.health_routes import router as health_router
from raqe.api.query_routes import router as query_router
from raqe.config import get_settings
from raqe.middleware.collection_namespace import CollectionNamespaceMiddleware

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(CollectionNamespaceMiddleware)

app.include_router(health_router)
app.include_router(query_router)
app.include_router(collection_router)
