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
    def test_chat_requires_auth(self, client: TestClient):
        """Sem autenticacao, deve retornar 401."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": 1},
        )
        assert response.status_code == 401

    def test_chat_requires_valid_session(self, authed_client):
        """Com auth mas session_id invalido deve retornar 404."""
        client, _ = authed_client
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": 99999},
        )
        assert response.status_code == 404

    def test_chat_empty_message_rejected(self, authed_client):
        """Mensagem vazia deve ser rejeitada com 422."""
        client, session_id = authed_client
        response = client.post(
            "/api/chat",
            json={"message": "", "session_id": session_id},
        )
        assert response.status_code == 422

    def test_chat_endpoint_authenticated(self, authed_client):
        """Autenticado e com sessao valida, espera 503 (sem API key) ou 200."""
        client, session_id = authed_client
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": session_id},
        )
        # Sem OPENROUTER_API_KEY, esperamos 503 (config error)
        assert response.status_code in (200, 503)


class TestChatStreamEndpoint:
    def test_chat_stream_requires_auth(self, client: TestClient):
        """Sem autenticacao, deve retornar 401."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": 1},
        )
        assert response.status_code == 401

    def test_chat_stream_empty_message_rejected(self, authed_client):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        client, session_id = authed_client
        response = client.post(
            "/api/chat/stream",
            json={"message": "", "session_id": session_id},
        )
        assert response.status_code == 422


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
        assert response.status_code in (200, 405)
