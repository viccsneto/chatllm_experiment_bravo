from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestCreateSession:
    def test_create_session(self, client, auth_headers):
        """Deve criar uma nova sessao e retornar 201 com id."""
        response = client.post("/api/sessions", json={}, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] is None

    def test_create_session_requires_auth(self, client):
        """Sem token, criar sessao retorna 401."""
        response = client.post("/api/sessions", json={})
        assert response.status_code == 401


class TestListSessions:
    def test_list_sessions(self, client, auth_headers):
        """Deve listar sessoes do usuario."""
        # Criar 2 sessoes
        client.post("/api/sessions", json={}, headers=auth_headers)
        client.post("/api/sessions", json={}, headers=auth_headers)

        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_sessions_empty(self, client, auth_headers):
        """Usuario sem sessoes deve receber lista vazia."""
        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sessions_requires_auth(self, client):
        """Sem token, listar retorna 401."""
        response = client.get("/api/sessions")
        assert response.status_code == 401

    def test_session_isolation_between_users(self, client):
        """Usuario B nao deve ver sessoes do usuario A."""
        # User A cria sessao
        resp_a = client.post("/api/signup", json={
            "email": "user_a@teste.com", "password": "senha123",
        })
        token_a = resp_a.json()["access_token"]
        client.post("/api/sessions", json={}, headers={"Authorization": f"Bearer {token_a}"})

        # User B lista sessoes
        resp_b = client.post("/api/signup", json={
            "email": "user_b@teste.com", "password": "senha123",
        })
        token_b = resp_b.json()["access_token"]
        response = client.get("/api/sessions", headers={"Authorization": f"Bearer {token_b}"})
        assert response.status_code == 200
        assert response.json() == []


class TestGetSessionMessages:
    def test_get_session_messages(self, client, auth_headers, auth_token):
        """Deve retornar mensagens de uma sessao especifica."""
        # Criar sessao
        sess_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = sess_resp.json()["id"]

        # Enviar mensagem via chat
        client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": session_id},
            headers=auth_headers,
        )

        response = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "assistant"

    def test_get_session_messages_not_found(self, client, auth_headers):
        """Sessao inexistente retorna 404."""
        response = client.get("/api/sessions/99999/messages", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateSession:
    def test_update_session_title(self, client, auth_headers):
        """Deve atualizar o titulo de uma sessao."""
        sess_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = sess_resp.json()["id"]

        response = client.patch(
            f"/api/sessions/{session_id}",
            json={"title": "Meu Chat"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Meu Chat"

    def test_update_session_not_found(self, client, auth_headers):
        """Atualizar sessao inexistente retorna 404."""
        response = client.patch(
            "/api/sessions/99999",
            json={"title": "Teste"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteSession:
    def test_delete_session(self, client, auth_headers):
        """Deve excluir uma sessao e retornar 204."""
        sess_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = sess_resp.json()["id"]

        response = client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verificar que foi excluida
        get_resp = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_session_not_found(self, client, auth_headers):
        """Excluir sessao inexistente retorna 404."""
        response = client.delete("/api/sessions/99999", headers=auth_headers)
        assert response.status_code == 404


class TestChatWithSession:

    def _mock_generate_reply(self, reply="Mock reply", model="mock-model"):
        """Retorna um pad decorator que mocka generate_reply no router."""
        return patch(
            "backend.routers.chat.generate_reply",
            AsyncMock(return_value=(reply, model)),
        )

    def test_chat_auto_creates_session(self, client, auth_headers):
        """Enviar mensagem sem session_id deve criar nova sessao automaticamente."""
        with self._mock_generate_reply():
            response = client.post(
                "/api/chat",
                json={"message": "Ola"},
                headers=auth_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], int)

    def test_chat_with_existing_session(self, client, auth_headers):
        """Enviar mensagem com session_id existente."""
        sess_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = sess_resp.json()["id"]

        with self._mock_generate_reply():
            response = client.post(
                "/api/chat",
                json={"message": "Ola", "session_id": session_id},
                headers=auth_headers,
            )
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

    def test_chat_with_invalid_session(self, client, auth_headers):
        """Enviar mensagem com session_id inexistente retorna 404."""
        with self._mock_generate_reply():
            response = client.post(
                "/api/chat",
                json={"message": "Ola", "session_id": 99999},
                headers=auth_headers,
            )
        assert response.status_code == 404

    def test_messages_persisted_to_session(self, client, auth_headers):
        """Apos enviar mensagem, as mensagens devem estar na sessao."""
        sess_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = sess_resp.json()["id"]

        with self._mock_generate_reply():
            client.post(
                "/api/chat",
                json={"message": "Minha pergunta", "session_id": session_id},
                headers=auth_headers,
            )

        # Recuperar mensagens da sessao
        msgs_resp = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers)
        assert msgs_resp.status_code == 200
        msgs = msgs_resp.json()
        assert len(msgs) >= 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Minha pergunta"
        assert msgs[1]["role"] == "assistant"

    def test_session_updated_at_changes_after_message(self, client, auth_headers):
        """Apos enviar mensagem, updated_at da sessao deve ser atualizado."""
        sess_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = sess_resp.json()["id"]
        created = sess_resp.json()["updated_at"]

        with self._mock_generate_reply():
            client.post(
                "/api/chat",
                json={"message": "Ola", "session_id": session_id},
                headers=auth_headers,
            )

        # Recarregar sessao
        sessions_resp = client.get("/api/sessions", headers=auth_headers)
        sessions = sessions_resp.json()
        target = next(s for s in sessions if s["id"] == session_id)
        assert target["updated_at"] > created

    def test_chat_stream_persists_messages(self, client, auth_headers):
        """O stream de chat deve persistir mensagens na sessao."""
        from unittest.mock import AsyncMock, MagicMock, patch

        sess_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = sess_resp.json()["id"]

        async def mock_aiter_lines():
            yield 'data: {"choices":[{"delta":{"content":"Resposta"}}]}'
            yield "data: [DONE]"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_aiter_lines

        class FakeStreamCtx:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, *args):
                pass

        class FakeClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            def stream(self, *args, **kwargs):
                return FakeStreamCtx()

        with patch("backend.services.openrouter.OPENROUTER_API_KEY", "sk-test"):
            with patch("httpx.AsyncClient", return_value=FakeClient()):
                response = client.post(
                    "/api/chat/stream",
                    json={"message": "Oi", "session_id": session_id},
                    headers=auth_headers,
                )
                # Ler o streaming para que o event_generator execute
                response.read()

        # Verificar mensagens persistidas
        msgs_resp = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers)
        assert msgs_resp.status_code == 200
        msgs = msgs_resp.json()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Oi"
        assert msgs[1]["role"] == "assistant"
        assert "Resposta" in msgs[1]["content"]