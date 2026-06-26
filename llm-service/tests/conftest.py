from fastapi.testclient import TestClient
import pytest

from llm_service.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())
