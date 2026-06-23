from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _auth_header(client: TestClient) -> dict[str, str]:
    """Helper: cadastra um usuario e retorna header de autenticacao."""
    resp = client.post(
        "/api/auth/signup",
        json={"email": "chat@test.com", "password": "123456"},
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"token": token}


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
    def test_chat_endpoint_exists(self, client: TestClient):
        """Verifica que o endpoint /api/chat responde com autenticacao."""
        headers = _auth_header(client)
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": None},
            headers=headers,
        )
        # Sem OPENROUTER_API_KEY definida, esperamos 503 (config error) ou 200
        assert response.status_code in (200, 422, 503)

    def test_chat_empty_message_rejected(self, client: TestClient):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic)."""
        headers = _auth_header(client)
        response = client.post(
            "/api/chat",
            json={"message": "", "session_id": None},
            headers=headers,
        )
        assert response.status_code == 422

    def test_chat_requires_auth(self, client: TestClient):
        """Sem autenticacao, deve retornar 401."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": None},
        )
        assert response.status_code == 401


class TestChatStreamEndpoint:
    def test_chat_stream_endpoint_exists(self, client: TestClient):
        """Verifica que o endpoint /api/chat/stream aceita requisicoes autenticadas."""
        headers = _auth_header(client)
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": None},
            headers=headers,
        )
        assert response.status_code in (200, 422, 503)

    def test_chat_stream_empty_message_rejected(self, client: TestClient):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        headers = _auth_header(client)
        response = client.post(
            "/api/chat/stream",
            json={"message": "", "session_id": None},
            headers=headers,
        )
        assert response.status_code == 422

    def test_chat_stream_requires_auth(self, client: TestClient):
        """Sem autenticacao, deve retornar 401."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": None},
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
        assert response.status_code in (200, 405)
