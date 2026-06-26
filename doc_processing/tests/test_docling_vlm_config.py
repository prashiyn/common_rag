from __future__ import annotations

from unittest.mock import MagicMock, patch

from docling.datamodel.vlm_engine_options import VlmEngineType

from doc_processing.llm_runtime.docling_vlm import (
    build_ollama_vlm_engine_options,
    get_ollama_chat_completions_url,
)


@patch("doc_processing.llm_runtime.docling_vlm.get_settings")
def test_ollama_chat_completions_url(mock_settings: MagicMock) -> None:
    mock_settings.return_value.ollama_base_url = "http://ollama:11434"

    assert get_ollama_chat_completions_url() == "http://ollama:11434/v1/chat/completions"


@patch("doc_processing.llm_runtime.docling_vlm.get_settings")
@patch("doc_processing.llm_runtime.docling_vlm.get_use_case_llm_config")
def test_build_ollama_vlm_engine_options(mock_case_cfg: MagicMock, mock_settings: MagicMock) -> None:
    mock_settings.return_value.ollama_base_url = "http://ollama:11434"
    mock_case_cfg.return_value = {
        "model": "ibm/granite-docling:latest",
        "timeout_seconds": 90,
        "api_params": {"temperature": 0.0, "max_tokens": 8192},
    }

    opts = build_ollama_vlm_engine_options("docling_pdf_vlm")
    assert opts.engine_type == VlmEngineType.API_OLLAMA
    assert str(opts.url) == "http://ollama:11434/v1/chat/completions"
    assert opts.params["model"] == "ibm/granite-docling:latest"
    assert opts.params["temperature"] == 0.0
    assert opts.timeout == 90.0


@patch("doc_processing.llm_runtime.docling_vlm.get_settings")
@patch("doc_processing.llm_runtime.docling_vlm.get_use_case_llm_config")
def test_ollama_native_model_strips_llm_service_prefix(
    mock_case_cfg: MagicMock, mock_settings: MagicMock
) -> None:
    mock_settings.return_value.ollama_base_url = "http://localhost:11434"
    mock_case_cfg.return_value = {
        "model": "ollama/ibm/granite-docling:latest",
        "timeout_seconds": 60,
    }

    opts = build_ollama_vlm_engine_options("docling_pdf_vlm")
    assert opts.params["model"] == "ibm/granite-docling:latest"
