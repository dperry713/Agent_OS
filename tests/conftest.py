import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Mock the engine and metadata create_all BEFORE importing app
with patch("app.db.session.engine") as mock_engine:
    with patch("app.models.base.Base.metadata.create_all"):
        from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c