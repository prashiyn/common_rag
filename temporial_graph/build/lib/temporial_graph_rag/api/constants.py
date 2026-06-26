from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[4]
ONTOLOGIES_DIR = REPO_ROOT / "ontologies"


class CreateCollectionRequest(BaseModel):
    collection_name: str = Field(..., min_length=1)
    ontology_id: str = Field(..., min_length=1)


class CollectionResponse(BaseModel):
    collection_name: str
    ontology_id: str


class CollectionDetailResponse(CollectionResponse):
    ontology_version: str | None = None
    registry_backend: str


class CollectionGetOrCreateResponse(CollectionDetailResponse):
    created: bool
