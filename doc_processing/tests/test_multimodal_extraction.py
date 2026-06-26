from __future__ import annotations

from doc_processing.ffp.multimodal.llm_response import parse_relevance_response


def test_parse_relevant_false_returns_none() -> None:
    assert parse_relevance_response('{"relevant":false}') is None
    assert parse_relevance_response('{"relevant": false, "reason": "logo"}') is None


def test_parse_relevant_true_with_text() -> None:
    raw = '{"relevant":true,"text":"Revenue rose 12% to INR 1,234 crore in FY24."}'
    assert parse_relevance_response(raw) == "Revenue rose 12% to INR 1,234 crore in FY24."


def test_parse_rejects_generic_advice_prose() -> None:
    prose = (
        "The image appears to be a financial chart, but without specific data it is "
        "challenging to provide a detailed analysis. However, I can offer a general "
        "approach to interpreting such charts."
    )
    assert parse_relevance_response(prose) is None


def test_parse_rejects_numbered_howto() -> None:
    prose = (
        "1. Identify key metrics.\n2. Trend analysis.\n3. Comparative analysis.\n"
        "4. Anomalies.\n5. Forecasting."
    )
    assert parse_relevance_response(prose) is None


def test_parse_json_fence() -> None:
    raw = '```json\n{"relevant":true,"text":"Net profit margin 8.2%."}\n```'
    assert parse_relevance_response(raw) == "Net profit margin 8.2%."
