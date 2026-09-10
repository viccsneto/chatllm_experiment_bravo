from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.models import ChatSession


class TestSessionEndpoints:
    def test_sessions_require_authentication(self, client: TestClient):
        assert client.get("/api/sessions").status_code == 401
        assert client.post("/api/sessions").status_code == 401
        assert client.get("/api/sessions/1").status_code == 401

    def test_create_list_and_get_session(self, authenticated_client: TestClient):
        created_response = authenticated_client.post("/api/sessions")
        assert created_response.status_code == 201
        created = created_response.json()
        assert created["title"] is None

        listed_response = authenticated_client.get("/api/sessions")
        assert listed_response.status_code == 200
        assert [session["id"] for session in listed_response.json()] == [created["id"]]

        detail_response = authenticated_client.get(f"/api/sessions/{created['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == created["id"]
        assert detail_response.json()["messages"] == []

    def test_session_is_not_visible_to_another_user(self, client: TestClient):
        first_register = client.post(
            "/api/auth/register",
            json={"email": "primeiro@example.com", "password": "senha-segura"},
        )
        assert first_register.status_code == 201
        private_session = client.post("/api/sessions").json()

        client.cookies.clear()
        second_register = client.post(
            "/api/auth/register",
            json={"email": "segundo@example.com", "password": "senha-segura"},
        )
        assert second_register.status_code == 201

        assert client.get("/api/sessions").json() == []
        forbidden_detail = client.get(f"/api/sessions/{private_session['id']}")
        assert forbidden_detail.status_code == 404

    def test_chat_rejects_session_owned_by_another_user(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "dono@example.com", "password": "senha-segura"},
        )
        private_session = client.post("/api/sessions").json()

        client.cookies.clear()
        client.post(
            "/api/auth/register",
            json={"email": "intruso@example.com", "password": "senha-segura"},
        )
        response = client.post(
            "/api/chat",
            json={"message": "Tentativa", "session_id": private_session["id"]},
        )
        assert response.status_code == 404

    def test_completed_chat_moves_session_to_top(self, authenticated_client: TestClient):
        first = authenticated_client.post("/api/sessions").json()
        second = authenticated_client.post("/api/sessions").json()

        with patch(
            "backend.routers.chat.generate_reply",
            new=AsyncMock(return_value=("Resposta", "test-model")),
        ):
            response = authenticated_client.post(
                "/api/chat",
                json={"message": "Atualize esta", "session_id": first["id"]},
            )

        assert response.status_code == 200
        listed = authenticated_client.get("/api/sessions").json()
        assert [session["id"] for session in listed] == [first["id"], second["id"]]

    def test_recent_message_breaks_timestamp_tie(
        self,
        authenticated_client: TestClient,
        db_session,
    ):
        first = authenticated_client.post("/api/sessions").json()
        second = authenticated_client.post("/api/sessions").json()
        frozen = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        for session in db_session.query(ChatSession).all():
            session.created_at = frozen
            session.updated_at = frozen
        db_session.commit()

        with patch(
            "backend.routers.chat.generate_reply",
            new=AsyncMock(return_value=("Resposta", "test-model")),
        ), patch("backend.routers.chat._utc_now", return_value=frozen):
            response = authenticated_client.post(
                "/api/chat",
                json={"message": "Atualize esta", "session_id": first["id"]},
            )

        assert response.status_code == 200
        listed = authenticated_client.get("/api/sessions").json()
        assert [session["id"] for session in listed] == [first["id"], second["id"]]
