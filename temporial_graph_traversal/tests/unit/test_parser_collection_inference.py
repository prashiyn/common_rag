import pytest

from raqe.agent.parser import parse_query


def test_parser_uses_alias_mapping_for_collection() -> None:
    parsed = parse_query("Why did revenue increase for ril in Q1 FY24?")
    assert parsed["collection"] == "tgt_graph_RELIANCE"


def test_parser_does_not_use_temporal_token_as_collection() -> None:
    with pytest.raises(ValueError, match="collection is required"):
        parse_query("Why did revenue increase in Q1 FY24?")


def test_parser_accepts_explicit_collection_override() -> None:
    parsed = parse_query("Why did revenue increase in Q1 FY24?", collection_override="INFY")
    assert parsed["collection"] == "tgt_graph_INFY"
