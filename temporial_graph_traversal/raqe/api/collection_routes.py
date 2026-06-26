from fastapi import APIRouter

from raqe.api.errors import collection_not_found_error
from raqe.models.collection import CollectionMetadata, CollectionSummary, GetOrCreateCollectionRequest
from raqe.services.collections import CollectionService

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("", response_model=list[CollectionSummary])
def list_collections() -> list[CollectionSummary]:
    service = CollectionService()
    return service.list_collections()


@router.get("/{collection_id}", response_model=CollectionMetadata)
def get_collection_metadata(collection_id: str) -> CollectionMetadata:
    service = CollectionService()
    metadata = service.get_collection_metadata(collection_id)
    if metadata is None:
        raise collection_not_found_error(collection_id)
    return metadata


@router.post("/get-or-create", response_model=CollectionSummary)
def get_or_create_collection(payload: GetOrCreateCollectionRequest) -> CollectionSummary:
    service = CollectionService()
    return service.get_or_create_collection(collection_id=payload.collection_id, name=payload.name)
