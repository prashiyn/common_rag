from __future__ import annotations

from unittest.mock import patch

from doc_processing.debug_trace import create_debug_run_dir, is_debug_enabled, write_debug_text


@patch("doc_processing.debug_trace.get_settings")
def test_debug_disabled_by_default(mock_settings) -> None:
    mock_settings.return_value.debug = False
    mock_settings.return_value.doc_processing_debug = None
    assert is_debug_enabled() is False
    assert create_debug_run_dir("chunk", "doc") is None


@patch("doc_processing.debug_trace.get_settings")
def test_debug_enabled_when_debug_true(mock_settings, tmp_path) -> None:
    mock_settings.return_value.debug = True
    mock_settings.return_value.doc_processing_debug = None
    mock_settings.return_value.temp_dir = str(tmp_path)

    assert is_debug_enabled() is True
    run_dir = create_debug_run_dir("chunk", "doc")
    assert run_dir is not None


@patch("doc_processing.debug_trace.get_settings")
def test_debug_enabled_legacy_doc_processing_debug(mock_settings, tmp_path) -> None:
    mock_settings.return_value.debug = False
    mock_settings.return_value.doc_processing_debug = "DEBUG"
    mock_settings.return_value.temp_dir = str(tmp_path)

    assert is_debug_enabled() is True


@patch("doc_processing.debug_trace.get_settings")
def test_debug_artifacts_written_when_enabled(mock_settings, tmp_path) -> None:
    mock_settings.return_value.debug = True
    mock_settings.return_value.doc_processing_debug = None
    mock_settings.return_value.temp_dir = str(tmp_path)

    run_dir = create_debug_run_dir("chunk", "my doc")
    assert run_dir is not None
    assert run_dir.is_dir()
    write_debug_text(run_dir, "converted.md", "# hello")
    assert (run_dir / "converted.md").read_text(encoding="utf-8") == "# hello"
