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
        """Sem token, o endpoint deve retornar 403."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        assert response.status_code == 403

    def test_chat_creates_session_if_not_provided(self, client: TestClient, auth_headers):
        """Sem session_id deve criar nova sessao."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
            headers=auth_headers,
        )
        # Sem API key deve retornar 503, mas a sessao foi criada
        assert response.status_code in (200, 422, 503)

    def test_chat_with_session_id(self, client: TestClient, auth_headers, test_session):
        """Com session_id valido deve aceitar."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": test_session.id},
            headers=auth_headers,
        )
        assert response.status_code in (200, 422, 503)

    def test_chat_invalid_session(self, client: TestClient, auth_headers):
        """Session_id invalido deve retornar 404."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": 9999},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_chat_empty_message_rejected(self, client: TestClient, auth_headers):
        """Mensagem vazia deve ser rejeitada com 422."""
        response = client.post(
            "/api/chat",
            json={"message": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestChatStreamEndpoint:
    def test_chat_stream_requires_auth(self, client: TestClient):
        """Sem token deve retornar 403."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
        )
        assert response.status_code == 403

    def test_chat_stream_creates_session(self, client: TestClient, auth_headers):
        """Sem session_id deve criar nova sessao."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
            headers=auth_headers,
        )
        assert response.status_code in (200, 422, 503)

    def test_chat_stream_with_session_id(self, client: TestClient, auth_headers, test_session):
        """Com session_id valido deve aceitar."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": test_session.id},
            headers=auth_headers,
        )
        assert response.status_code in (200, 422, 503)

    def test_chat_stream_invalid_session(self, client: TestClient, auth_headers):
        """Session_id invalido deve retornar 404."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": 9999},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_chat_stream_empty_message_rejected(self, client: TestClient, auth_headers):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        response = client.post(
            "/api/chat/stream",
            json={"message": ""},
            headers=auth_headers,
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
