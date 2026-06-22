from __future__ import annotations

from fastapi.testclient import TestClient

from backend.models import ChatSession, User


def _register_and_login(client: TestClient, email: str = "sess@teste.com") -> str:
    """Helper: register + login, return access token."""
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "senha123"},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


class TestSessionsList:
    def test_list_sessions_empty(self, client: TestClient):
        """Usuario recebe lista vazia quando nao tem sessoes."""
        token = _register_and_login(client)
        resp = client.get("/api/sessions", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_sessions_after_creation(self, client: TestClient):
        """Lista retorna sessoes criadas."""
        token = _register_and_login(client, "list@teste.com")
        client.post("/api/sessions", headers={"Authorization": f"Bearer {token}"}, json={})
        client.post("/api/sessions", headers={"Authorization": f"Bearer {token}"}, json={})
        resp = client.get("/api/sessions", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_sessions_other_user_not_visible(self, client: TestClient):
        """Sessoes de outro usuario nao aparecem na lista."""
        token1 = _register_and_login(client, "user1@teste.com")
        token2 = _register_and_login(client, "user2@teste.com")
        client.post("/api/sessions", headers={"Authorization": f"Bearer {token1}"}, json={})
        resp = client.get("/api/sessions", headers={"Authorization": f"Bearer {token2}"})
        assert resp.json() == []

    def test_list_sessions_requires_auth(self, client: TestClient):
        """Requisicao sem token deve ser rejeitada."""
        resp = client.get("/api/sessions")
        assert resp.status_code in (401, 403)


class TestSessionsCreate:
    def test_create_session(self, client: TestClient):
        """Criar sessao retorna 201 com dados."""
        token = _register_and_login(client, "create@teste.com")
        resp = client.post("/api/sessions", headers={"Authorization": f"Bearer {token}"}, json={})
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] is not None
        assert data["title"] is None

    def test_create_session_requires_auth(self, client: TestClient):
        """Criar sessao sem token deve ser rejeitado."""
        resp = client.post("/api/sessions", json={})
        assert resp.status_code in (401, 403)


class TestSessionsGet:
    def test_get_session(self, client: TestClient):
        """Obter sessao especifica retorna dados corretos."""
        token = _register_and_login(client, "get@teste.com")
        create_resp = client.post("/api/sessions", headers={"Authorization": f"Bearer {token}"}, json={})
        session_id = create_resp.json()["id"]
        resp = client.get(
            f"/api/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id

    def test_get_session_not_found(self, client: TestClient):
        """Sessao inexistente retorna 404."""
        token = _register_and_login(client, "notfound@teste.com")
        resp = client.get("/api/sessions/99999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_get_session_other_user(self, client: TestClient):
        """Sessao de outro usuario retorna 404."""
        token1 = _register_and_login(client, "own@teste.com")
        token2 = _register_and_login(client, "other@teste.com")
        create_resp = client.post("/api/sessions", headers={"Authorization": f"Bearer {token1}"}, json={})
        session_id = create_resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 404


class TestSessionsRename:
    def test_rename_session(self, client: TestClient):
        """Renomear sessao funciona e persiste."""
        token = _register_and_login(client, "rename@teste.com")
        create_resp = client.post("/api/sessions", headers={"Authorization": f"Bearer {token}"}, json={})
        session_id = create_resp.json()["id"]
        resp = client.patch(
            f"/api/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Novo Titulo"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Novo Titulo"


class TestSessionsDelete:
    def test_delete_session(self, client: TestClient):
        """Deletar sessao retorna 204."""
        token = _register_and_login(client, "del@teste.com")
        create_resp = client.post("/api/sessions", headers={"Authorization": f"Bearer {token}"}, json={})
        session_id = create_resp.json()["id"]
        resp = client.delete(
            f"/api/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    def test_delete_nonexistent_session(self, client: TestClient):
        """Deletar sessao inexistente retorna 404."""
        token = _register_and_login(client, "delnf@teste.com")
        resp = client.delete("/api/sessions/99999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


class TestSessionsAuth:
    def test_all_endpoints_require_auth(self, client: TestClient):
        """Todos os endpoints de sessao exigem autenticacao."""
        assert client.get("/api/sessions").status_code in (401, 403)
        assert client.post("/api/sessions", json={}).status_code in (401, 403)
        assert client.get("/api/sessions/1").status_code in (401, 403)
        assert client.patch("/api/sessions/1", json={"title": "x"}).status_code in (401, 403)
        assert client.delete("/api/sessions/1").status_code in (401, 403)