import os
import sys
from contextlib import asynccontextmanager

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graph.utils.collection_id_middleware import CollectionIdMiddleware
from graph.utils.logger import logger
from logging_config import init_logging
from routers.graph_api import router as graph_api_router
from routers.health import router as health_router
from state import GRAPH_REPOSITORY


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_fn = getattr(GRAPH_REPOSITORY, "close", None)
    if callable(close_fn):
        close_fn()
        logger.info("Graph repository closed")


app = FastAPI(title="graph Unified Interface", version="1.0.0", lifespan=lifespan)
init_logging()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CollectionIdMiddleware)

app.include_router(health_router)
app.include_router(graph_api_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=20050)
