import pytest

from raqe.collection_namespace import (
    INTERNAL_PREFIX,
    rewrite_collections_path,
    to_external,
    to_internal,
    transform_inbound_payload,
    transform_outbound_payload,
)


def test_to_internal_adds_prefix() -> None:
    assert to_internal("RELIANCE") == f"{INTERNAL_PREFIX}RELIANCE"


def test_to_internal_is_idempotent() -> None:
    internal = to_internal("INFY")
    assert to_internal(internal) == internal


def test_to_internal_normalizes_case_variant_prefix() -> None:
    assert to_internal("TGT_GRAPH_INFY") == f"{INTERNAL_PREFIX}INFY"


def test_to_external_strips_prefix() -> None:
    assert to_external(f"{INTERNAL_PREFIX}RELIANCE") == "RELIANCE"


def test_rewrite_collections_path_for_external_id() -> None:
    assert rewrite_collections_path("/collections/RELIANCE") == f"/collections/{INTERNAL_PREFIX}RELIANCE"


def test_rewrite_collections_path_skips_get_or_create() -> None:
    assert rewrite_collections_path("/collections/get-or-create") is None


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"collection": "AB"}, {"collection": f"{INTERNAL_PREFIX}AB"}),
        ({"nested": {"collection_id": "XY"}}, {"nested": {"collection_id": f"{INTERNAL_PREFIX}XY"}}),
        ({"collection": ""}, {"collection": ""}),
    ],
)
def test_transform_inbound_payload(payload, expected) -> None:
    assert transform_inbound_payload(payload) == expected


def test_transform_outbound_payload_collection_keys() -> None:
    internal = f"{INTERNAL_PREFIX}RELIANCE"
    out = transform_outbound_payload(
        {"parsed_query": {"collection": internal}, "execution": {"chunks": [{"collection_id": internal}]}}
    )
    assert out["parsed_query"]["collection"] == "RELIANCE"
    assert out["execution"]["chunks"][0]["collection_id"] == "RELIANCE"


def test_transform_outbound_strips_prefixed_id_and_name() -> None:
    internal = f"{INTERNAL_PREFIX}INFY"
    out = transform_outbound_payload({"id": internal, "name": internal})
    assert out == {"id": "INFY", "name": "INFY"}


def test_transform_outbound_leaves_document_id() -> None:
    assert transform_outbound_payload({"document_id": "doc_1"}) == {"document_id": "doc_1"}
