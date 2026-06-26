"""Runtime clients for doc-processing -> llm-service communication."""

from doc_processing.llm_runtime.docling_vlm import (
    build_ollama_vlm_engine_options,
    build_picture_description_options,
    build_vlm_convert_options,
    get_ollama_chat_completions_url,
)
from doc_processing.llm_runtime.http_client import HttpLLMRuntime
from doc_processing.llm_runtime.llm_service_client import LlmServiceClient

__all__ = [
    "HttpLLMRuntime",
    "LlmServiceClient",
    "build_ollama_vlm_engine_options",
    "build_picture_description_options",
    "build_vlm_convert_options",
    "get_ollama_chat_completions_url",
]
