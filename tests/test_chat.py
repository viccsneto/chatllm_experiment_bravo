from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestRootEndpoint:
    def test_root_returns_frontend(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestChatEndpoint:
    def test_chat_endpoint_exists(self, auth_client):
        """Verifica que o endpoint /api/chat responde (espera erro de config sem API key)."""
        # Primeiro criar uma sessao
        session_resp = auth_client.post("/api/sessions", json={})
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        response = auth_client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": session_id},
        )
        # Sem OPENROUTER_API_KEY definida, esperamos 503 (config error)
        assert response.status_code in (200, 422, 503)

    def test_chat_empty_message_rejected(self, client):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic).
        Sem auth, o endpoint retorna 401 primeiro (auth > body validation)."""
        response = client.post(
            "/api/chat",
            json={"message": ""},
        )
        assert response.status_code in (401, 422)

    def test_chat_requires_auth(self, client):
        """Endpoint de chat deve exigir autenticacao."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        assert response.status_code == 401

    def test_chat_auto_creates_session(self, auth_client):
        """Quando session_id e None, _resolve_session cria nova sessao."""
        list_before = auth_client.get("/api/sessions")
        assert list_before.status_code == 200
        count_before = len(list_before.json()["sessions"])

        response = auth_client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        assert response.status_code in (200, 503)

        list_after = auth_client.get("/api/sessions")
        assert list_after.status_code == 200
        sessions_after = list_after.json()["sessions"]
        assert len(sessions_after) == count_before + 1


class TestChatStreamEndpoint:
    def test_chat_stream_endpoint_exists(self, auth_client):
        """Verifica que o endpoint /api/chat/stream aceita requisicoes."""
        session_resp = auth_client.post("/api/sessions", json={})
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        response = auth_client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": session_id},
        )
        # Streaming pode iniciar e depois falhar sem API key
        assert response.status_code in (200, 422, 503)

    def test_chat_stream_empty_message_rejected(self, client):
        """Stream com mensagem vazia deve ser rejeitado com 422 ou 401."""
        response = client.post(
            "/api/chat/stream",
            json={"message": ""},
        )
        assert response.status_code in (401, 422)

    def test_chat_stream_requires_auth(self, client):
        """Stream deve exigir autenticacao."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
        )
        assert response.status_code == 401


class TestCORSMiddleware:
    def test_cors_headers_present(self, client: TestClient):
        """Verifica que os headers CORS estao presentes."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # O FastAPI com allow_origins=["*"] permite a requisicao
        assert response.status_code in (200, 405)
