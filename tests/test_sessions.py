from __future__ import annotations

from fastapi.testclient import TestClient


class TestListSessions:
    def test_list_sessions_empty(self, client: TestClient, auth_headers):
        """Deve retornar lista vazia quando nao ha sessoes."""
        response = client.get("/api/sessions/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sessions(self, client: TestClient, auth_headers, test_session):
        """Deve retornar sessoes do usuario."""
        response = client.get("/api/sessions/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_session.id

    def test_list_sessions_requires_auth(self, client: TestClient):
        """Sem token deve retornar 403."""
        response = client.get("/api/sessions/")
        assert response.status_code == 403


class TestCreateSession:
    def test_create_session_success(self, client: TestClient, auth_headers):
        """Deve criar nova sessao com sucesso."""
        response = client.post("/api/sessions/", headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] is None

    def test_create_session_requires_auth(self, client: TestClient):
        """Sem token deve retornar 403."""
        response = client.post("/api/sessions/")
        assert response.status_code == 403


class TestGetSessionMessages:
    def test_get_messages_empty(self, client: TestClient, auth_headers, test_session):
        """Sessao sem mensagens deve retornar lista vazia."""
        response = client.get(f"/api/sessions/{test_session.id}/messages", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_messages_not_found(self, client: TestClient, auth_headers):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/9999/messages", headers=auth_headers)
        assert response.status_code == 404

    def test_get_messages_other_user_returns_404(self, client: TestClient, auth_headers):
        """Sessao de outro usuario deve retornar 404."""
        response = client.get("/api/sessions/9999/messages", headers=auth_headers)
        assert response.status_code == 404


class TestDeleteSession:
    def test_delete_session_success(self, client: TestClient, auth_headers, test_session):
        """Deve deletar sessao com sucesso."""
        response = client.delete(f"/api/sessions/{test_session.id}", headers=auth_headers)
        assert response.status_code == 204

    def test_delete_session_not_found(self, client: TestClient, auth_headers):
        """Sessao inexistente deve retornar 404."""
        response = client.delete("/api/sessions/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_session_requires_auth(self, client: TestClient, test_session):
        """Sem token deve retornar 403."""
        response = client.delete(f"/api/sessions/{test_session.id}")
        assert response.status_code == 403