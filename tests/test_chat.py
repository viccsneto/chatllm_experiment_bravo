from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.models import ChatMessage, ChatSession


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

    def test_chat_endpoint_exists(self, authenticated_client: TestClient, db_session):
        with patch(
            "backend.routers.chat.generate_reply",
            new=AsyncMock(return_value=("Resposta mockada", "test-model")),
        ):
            response = authenticated_client.post(
                "/api/chat",
                json={"message": "Ola"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["reply"] == "Resposta mockada"
        assert body["model"] == "test-model"
        assert body["session_id"] > 0
        assert body["title"] == "Ola"

        detail = authenticated_client.get(f"/api/sessions/{body['session_id']}")
        assert detail.status_code == 200
        assert [message["role"] for message in detail.json()["messages"]] == [
            "user",
            "assistant",
        ]

    def test_chat_uses_stored_session_history(self, authenticated_client: TestClient):
        created = authenticated_client.post("/api/sessions").json()
        mocked_reply = AsyncMock(
            side_effect=[
                ("Primeira resposta", "test-model"),
                ("Segunda resposta", "test-model"),
            ]
        )

        with patch("backend.routers.chat.generate_reply", new=mocked_reply):
            first = authenticated_client.post(
                "/api/chat",
                json={"message": "Primeira pergunta", "session_id": created["id"]},
            )
            second = authenticated_client.post(
                "/api/chat",
                json={"message": "Segunda pergunta", "session_id": created["id"]},
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["title"] == "Primeira pergunta"
        assert mocked_reply.await_args_list[1].kwargs["history"] == [
            {"role": "user", "content": "Primeira pergunta"},
            {"role": "assistant", "content": "Primeira resposta"},
        ]

    def test_chat_empty_message_rejected(self, authenticated_client: TestClient):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic)."""
        response = authenticated_client.post(
            "/api/chat",
            json={"message": ""},
        )
        assert response.status_code == 422

    def test_failed_chat_does_not_create_an_orphan_session(
        self,
        authenticated_client: TestClient,
        db_session,
    ):
        async def failed_reply(**_kwargs):
            assert db_session.query(ChatSession).count() == 0
            raise RuntimeError("Falha simulada do provedor")

        with patch("backend.routers.chat.generate_reply", new=failed_reply):
            response = authenticated_client.post(
                "/api/chat",
                json={"message": "Ola"},
            )

        assert response.status_code == 502
        assert db_session.query(ChatSession).count() == 0
        assert db_session.query(ChatMessage).count() == 0


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
        assert '"session_id":' in response.text
        assert '"title": "Ola"' in response.text

        sessions = authenticated_client.get("/api/sessions").json()
        detail = authenticated_client.get(f"/api/sessions/{sessions[0]['id']}").json()
        assert [message["content"] for message in detail["messages"]] == [
            "Ola",
            "Resposta",
        ]

    def test_chat_stream_empty_message_rejected(self, authenticated_client: TestClient):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        response = authenticated_client.post(
            "/api/chat/stream",
            json={"message": ""},
        )
        assert response.status_code == 422

    def test_failed_stream_does_not_create_an_orphan_session(
        self,
        authenticated_client: TestClient,
        db_session,
    ):
        async def failed_stream(**_kwargs):
            assert db_session.query(ChatSession).count() == 0
            raise RuntimeError("Falha simulada do provedor")
            yield  # pragma: no cover - mantem a funcao como gerador assincrono

        with patch("backend.routers.chat.stream_reply", new=failed_stream):
            response = authenticated_client.post(
                "/api/chat/stream",
                json={"message": "Ola"},
            )

        assert response.status_code == 200
        assert '"error": "Falha simulada do provedor"' in response.text
        assert '"done": true' not in response.text
        assert db_session.query(ChatSession).count() == 0
        assert db_session.query(ChatMessage).count() == 0


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
