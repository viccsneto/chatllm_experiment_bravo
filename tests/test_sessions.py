from __future__ import annotations

from fastapi.testclient import TestClient


class TestCreateSession:
    def test_create_session(self, client: TestClient):
        """Deve criar uma nova sessao para o usuario logado."""
        response = client.post("/api/sessions")
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "Nova conversa"

    def test_create_session_requires_auth(self, client: TestClient):
        client.headers.clear()
        response = client.post("/api/sessions")
        assert response.status_code == 401


class TestListSessions:
    def test_list_sessions(self, client: TestClient):
        """Deve listar sessoes do usuario logado."""
        # Cria duas sessoes
        client.post("/api/sessions")
        client.post("/api/sessions")

        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) >= 2

    def test_list_sessions_requires_auth(self, client: TestClient):
        client.headers.clear()
        response = client.get("/api/sessions")
        assert response.status_code == 401


class TestGetSessionMessages:
    def test_get_messages_empty_session(self, client: TestClient):
        """Sessao sem mensagens deve retornar lista vazia."""
        sess = client.post("/api/sessions").json()
        response = client.get(f"/api/sessions/{sess['id']}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []

    def test_get_messages_nonexistent_session(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999/messages")
        assert response.status_code == 404

    def test_get_messages_requires_auth(self, client: TestClient):
        client.headers.clear()
        response = client.get("/api/sessions/1/messages")
        assert response.status_code == 401


class TestDeleteSession:
    def test_delete_session(self, client: TestClient):
        """Deve deletar sessao e retornar 204."""
        sess = client.post("/api/sessions").json()
        response = client.delete(f"/api/sessions/{sess['id']}")
        assert response.status_code == 204

        # Verifica que foi deletada
        response = client.get(f"/api/sessions/{sess['id']}/messages")
        assert response.status_code == 404

    def test_delete_nonexistent_session(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.delete("/api/sessions/99999")
        assert response.status_code == 404

    def test_delete_requires_auth(self, client: TestClient):
        client.headers.clear()
        response = client.delete("/api/sessions/1")
        assert response.status_code == 401