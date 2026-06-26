"""Shared pytest fixtures for API tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from doc_processing.config import get_settings
from doc_processing.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Synchronous TestClient over a fresh FastAPI app instance."""
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.delenv("DOC_PROCESSING_DEBUG", raising=False)
    get_settings.cache_clear()
    return TestClient(create_app())
