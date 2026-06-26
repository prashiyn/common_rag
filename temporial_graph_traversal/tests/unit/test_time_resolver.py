from raqe.agent.time_resolver import parse_time


def test_parse_q1_fy24() -> None:
    context = parse_time("Why did revenue move in Q1 FY24 for RELIANCE?")
    assert context.mode == "quarter"
    assert context.period == "Q1"
    assert context.fiscal_year == "FY2024"
    assert context.needs_fallback is False


def test_parse_explicit_between_range() -> None:
    context = parse_time("show movement between 2024-01-01 and 2024-03-31")
    assert context.mode == "explicit_range"
    assert context.start_date == "2024-01-01"
    assert context.end_date == "2024-03-31"


def test_parse_last_quarter_relative() -> None:
    context = parse_time("what changed in the last quarter")
    assert context.mode == "relative"
    assert context.relative_window == "last_quarter"


def test_parse_latest_fallback_mode() -> None:
    context = parse_time("latest results for RELIANCE")
    assert context.mode == "latest_fallback"
    assert context.needs_fallback is True


def test_parse_unknown_time_text_uses_fallback_without_crash() -> None:
    context = parse_time("summarize performance sometime soon")
    assert context.mode == "latest_fallback"
    assert context.needs_fallback is True
