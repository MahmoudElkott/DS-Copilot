# backend/tests/test_api.py
"""API route tests."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealth:
    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app_name"] == "DS-Copilot"

    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "DS-Copilot" in response.json()["app"]


class TestSessions:
    def test_create_session(self):
        response = client.post("/api/sessions", json={"project_name": "test"})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["project_name"] == "test"

    def test_list_sessions(self):
        response = client.get("/api/sessions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestSettings:
    def test_get_settings(self):
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "llm_provider" in data
        assert "temperature" in data

    def test_update_settings(self):
        response = client.put("/api/settings", json={"temperature": 0.5})
        assert response.status_code == 200


class TestStats:
    def test_get_stats(self):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_calls" in data
        assert "budget_remaining" in data


class TestUpload:
    def test_upload_invalid_extension(self):
        from io import BytesIO
        response = client.post(
            "/api/upload",
            files={"file": ("test.exe", BytesIO(b"data"), "application/octet-stream")},
        )
        assert response.status_code == 400
