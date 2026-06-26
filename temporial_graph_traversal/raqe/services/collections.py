from __future__ import annotations

from raqe.graph.neo4j_client import get_driver
from raqe.graph.queries import GET_COLLECTION_METADATA_QUERY, LIST_COLLECTIONS_QUERY, UPSERT_COLLECTION_QUERY
from raqe.models.collection import CollectionMetadata, CollectionSummary


class CollectionService:
    def __init__(self, driver=None):
        self.driver = driver or get_driver()

    def list_collections(self) -> list[CollectionSummary]:
        with self.driver.session() as session:
            rows = session.run(LIST_COLLECTIONS_QUERY)
            return [CollectionSummary(id=row["id"], name=row["name"]) for row in rows]

    def get_collection_metadata(self, collection_id: str) -> CollectionMetadata | None:
        with self.driver.session() as session:
            row = session.run(GET_COLLECTION_METADATA_QUERY, collection_id=collection_id).single()
            if not row:
                return None
            return CollectionMetadata(
                id=row["id"],
                name=row["name"],
                document_count=int(row["document_count"] or 0),
                chunk_count=int(row["chunk_count"] or 0),
                earliest_timestamp=row.get("earliest_timestamp"),
                latest_timestamp=row.get("latest_timestamp"),
            )

    def get_or_create_collection(self, collection_id: str, name: str | None = None) -> CollectionSummary:
        effective_name = name or collection_id
        with self.driver.session() as session:
            session.run(UPSERT_COLLECTION_QUERY, collection_id=collection_id)
            session.run(
                "MATCH (c:Collection {id: $collection_id}) SET c.name = $name RETURN c",
                collection_id=collection_id,
                name=effective_name,
            )
        return CollectionSummary(id=collection_id, name=effective_name)
