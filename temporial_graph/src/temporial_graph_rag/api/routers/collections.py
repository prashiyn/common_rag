from __future__ import annotations

from fastapi import APIRouter, HTTPException

from temporial_graph_rag.api.constants import (
    CollectionDetailResponse,
    CollectionGetOrCreateResponse,
    CollectionResponse,
    CreateCollectionRequest,
    ONTOLOGIES_DIR,
)
from temporial_graph_rag.api.registry_holder import registry
from temporial_graph_rag.ontology.loader import load_ontology

router = APIRouter()


@router.get("/v1/collections", response_model=list[CollectionResponse])
async def list_collections() -> list[CollectionResponse]:
    return [
        CollectionResponse(collection_name=b.collection_name, ontology_id=b.ontology_id)
        for b in registry.list_bindings()
    ]


@router.get("/v1/collections/{collection_name}", response_model=CollectionDetailResponse)
async def get_collection(collection_name: str) -> CollectionDetailResponse:
    binding = registry.get(collection_name)
    if binding is None:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist")
    ontology_version: str | None = None
    try:
        ontology = load_ontology(ONTOLOGIES_DIR, binding.ontology_id)
        ontology_version = ontology.ontology_version
    except FileNotFoundError:
        ontology_version = None
    return CollectionDetailResponse(
        collection_name=binding.collection_name,
        ontology_id=binding.ontology_id,
        ontology_version=ontology_version,
        registry_backend=registry.backend_kind(),
    )


@router.post("/v1/collections", response_model=CollectionResponse)
async def create_collection(body: CreateCollectionRequest) -> CollectionResponse:
    try:
        load_ontology(ONTOLOGIES_DIR, body.ontology_id)
        created = registry.create(body.collection_name, body.ontology_id)
        return CollectionResponse(
            collection_name=created.collection_name,
            ontology_id=created.ontology_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/v1/collections/get-or-create", response_model=CollectionGetOrCreateResponse)
async def get_or_create_collection(body: CreateCollectionRequest) -> CollectionGetOrCreateResponse:
    try:
        existing = registry.get(body.collection_name)
        if existing is not None:
            if existing.ontology_id != body.ontology_id:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Collection '{body.collection_name}' already exists with ontology "
                        f"'{existing.ontology_id}'"
                    ),
                )
            ontology = load_ontology(ONTOLOGIES_DIR, existing.ontology_id)
            return CollectionGetOrCreateResponse(
                collection_name=existing.collection_name,
                ontology_id=existing.ontology_id,
                ontology_version=ontology.ontology_version,
                registry_backend=registry.backend_kind(),
                created=False,
            )
        ontology = load_ontology(ONTOLOGIES_DIR, body.ontology_id)
        created = registry.create(body.collection_name, body.ontology_id)
        return CollectionGetOrCreateResponse(
            collection_name=created.collection_name,
            ontology_id=created.ontology_id,
            ontology_version=ontology.ontology_version,
            registry_backend=registry.backend_kind(),
            created=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
