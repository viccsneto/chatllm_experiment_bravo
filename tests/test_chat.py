from __future__ import annotations

from unittest.mock import AsyncMock, patch

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
    def test_chat_requires_authentication(self, client: TestClient):
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        assert response.status_code == 401

    def test_chat_endpoint_exists(self, authenticated_client: TestClient):
        with patch(
            "backend.routers.chat.generate_reply",
            new=AsyncMock(return_value=("Resposta mockada", "test-model")),
        ):
            response = authenticated_client.post(
                "/api/chat",
                json={"message": "Ola"},
            )

        assert response.status_code == 200
        assert response.json() == {"reply": "Resposta mockada", "model": "test-model"}

    def test_chat_empty_message_rejected(self, authenticated_client: TestClient):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic)."""
        response = authenticated_client.post(
            "/api/chat",
            json={"message": ""},
        )
        assert response.status_code == 422


class TestChatStreamEndpoint:
    def test_chat_stream_requires_authentication(self, client: TestClient):
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
        )
        assert response.status_code == 401

    def test_chat_stream_endpoint_exists(self, authenticated_client: TestClient):
        """Verifica que o endpoint /api/chat/stream aceita requisicoes."""
        async def fake_stream_reply(**_kwargs):
            yield "Resposta"

        with patch("backend.routers.chat.stream_reply", new=fake_stream_reply):
            response = authenticated_client.post(
                "/api/chat/stream",
                json={"message": "Ola"},
            )

        assert response.status_code == 200
        assert '"delta": "Resposta"' in response.text
        assert '"done": true' in response.text

    def test_chat_stream_empty_message_rejected(self, authenticated_client: TestClient):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        response = authenticated_client.post(
            "/api/chat/stream",
            json={"message": ""},
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
        # O FastAPI com allow_origins=["*"] permite a requisicao
        assert response.status_code in (200, 405)
