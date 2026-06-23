from __future__ import annotations

from fastapi.testclient import TestClient


class TestSessionCRUD:
    def test_list_sessions_empty(self, client: TestClient, auth_headers):
        """Deve retornar lista vazia quando nao ha sessoes."""
        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_create_session(self, client: TestClient, auth_headers):
        """Deve criar uma nova sessao."""
        response = client.post("/api/sessions", json={}, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "Nova conversa"
        assert "created_at" in data
        assert "updated_at" in data

    def test_list_sessions_after_create(self, client: TestClient, auth_headers):
        """Deve listar sessoes apos criar."""
        client.post("/api/sessions", json={}, headers=auth_headers)
        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_session(self, client: TestClient, auth_headers):
        """Deve retornar uma sessao especifica."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        response = client.get(f"/api/sessions/{created['id']}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_session_not_found(self, client: TestClient, auth_headers):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_session(self, client: TestClient, auth_headers):
        """Deve excluir uma sessao."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        response = client.delete(f"/api/sessions/{created['id']}", headers=auth_headers)
        assert response.status_code == 200
        # Verificar que foi removida
        get_resp = client.get(f"/api/sessions/{created['id']}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_rename_session(self, client: TestClient, auth_headers):
        """Deve renomear uma sessao."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        response = client.patch(
            f"/api/sessions/{created['id']}/rename",
            json={"title": "Meu titulo"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Meu titulo"

    def test_sessions_requires_auth(self, client: TestClient):
        """Sem token, endpoints de sessao devem retornar 401."""
        assert client.get("/api/sessions").status_code == 401
        assert client.post("/api/sessions", json={}).status_code == 401

    def test_session_messages(self, client: TestClient, auth_headers):
        """Deve retornar mensagens de uma sessao."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        response = client.get(f"/api/sessions/{created['id']}/messages", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_sessions_isolated_per_user(self, client: TestClient, auth_headers, db_session):
        """Sessoes de um usuario nao devem ser visiveis a outro."""
        from backend.models import User
        import bcrypt

        # Criar segundo usuario
        user2 = User(
            email="outro@teste.com",
            password_hash=bcrypt.hashpw(b"senha123", bcrypt.gensalt()).decode("utf-8"),
        )
        db_session.add(user2)
        db_session.commit()

        from backend.routers.auth import get_current_user
        from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM
        from datetime import datetime, timedelta, timezone
        from jose import jwt

        user2_token = jwt.encode(
            {"sub": user2.email, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        # User 1 cria sessao
        client.post("/api/sessions", json={}, headers=auth_headers)

        # User 2 ve lista vazia
        response = client.get("/api/sessions", headers=user2_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0