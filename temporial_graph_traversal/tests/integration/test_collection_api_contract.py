from fastapi.testclient import TestClient

from raqe.main import app
from raqe.models.collection import CollectionMetadata, CollectionSummary

client = TestClient(app)


def test_list_collections_api(monkeypatch) -> None:
    monkeypatch.setattr(
        "raqe.api.collection_routes.CollectionService.list_collections",
        lambda self: [CollectionSummary(id="tgt_graph_RELIANCE", name="tgt_graph_RELIANCE")],  # noqa: ARG005
    )
    response = client.get("/collections")
    assert response.status_code == 200
    assert response.json() == [{"id": "RELIANCE", "name": "RELIANCE"}]


def test_get_collection_metadata_api(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _get(self, collection_id: str) -> CollectionMetadata:  # noqa: ARG005
        captured["collection_id"] = collection_id
        return CollectionMetadata(
            id=collection_id,
            name=collection_id,
            document_count=2,
            chunk_count=30,
            earliest_timestamp="2024-01-01",
            latest_timestamp="2024-06-30",
        )

    monkeypatch.setattr("raqe.api.collection_routes.CollectionService.get_collection_metadata", _get)
    response = client.get("/collections/RELIANCE")
    assert response.status_code == 200
    assert captured.get("collection_id") == "tgt_graph_RELIANCE"
    payload = response.json()
    assert payload["id"] == "RELIANCE"
    assert payload["document_count"] == 2


def test_get_collection_metadata_not_found_api(monkeypatch) -> None:
    monkeypatch.setattr(
        "raqe.api.collection_routes.CollectionService.get_collection_metadata",
        lambda self, collection_id: None,  # noqa: ARG005
    )
    response = client.get("/collections/UNKNOWN")
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "collection_not_found"


def test_get_or_create_collection_api(monkeypatch) -> None:
    monkeypatch.setattr(
        "raqe.api.collection_routes.CollectionService.get_or_create_collection",
        lambda self, collection_id, name=None: CollectionSummary(  # noqa: ARG005
            id=collection_id,
            name=name or collection_id,
        ),
    )
    response = client.post("/collections/get-or-create", json={"collection_id": "INFY", "name": "Infosys"})
    assert response.status_code == 200
    assert response.json() == {"id": "INFY", "name": "Infosys"}
