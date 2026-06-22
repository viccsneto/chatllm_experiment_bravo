from __future__ import annotations

from fastapi.testclient import TestClient
from jose import jwt

from backend.config import JWT_ALGORITHM, JWT_SECRET
from backend.models import User


class TestAuthRegister:
    def test_register_new_user(self, client: TestClient):
        """Deve cadastrar um novo usuario e retornar token."""
        response = client.post(
            "/api/auth/register",
            json={"email": "novo@teste.com", "password": "senha123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "novo@teste.com"
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_register_duplicate_email(self, client: TestClient):
        """Email duplicado deve retornar 409 Conflict."""
        client.post(
            "/api/auth/register",
            json={"email": "dup@teste.com", "password": "senha123"},
        )
        response = client.post(
            "/api/auth/register",
            json={"email": "dup@teste.com", "password": "outrasenha"},
        )
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Email sem formato valido deve retornar 422."""
        response = client.post(
            "/api/auth/register",
            json={"email": "invalido", "password": "senha123"},
        )
        assert response.status_code == 422

    def test_register_short_password(self, client: TestClient):
        """Senha muito curta deve retornar 422 (min_length=6)."""
        response = client.post(
            "/api/auth/register",
            json={"email": "curta@teste.com", "password": "123"},
        )
        assert response.status_code == 422


class TestAuthLogin:
    def test_login_success(self, client: TestClient):
        """Login com credenciais validas deve retornar token."""
        # Primeiro cadastra
        client.post(
            "/api/auth/register",
            json={"email": "login@teste.com", "password": "senha123"},
        )
        # Depois login
        response = client.post(
            "/api/auth/login",
            json={"email": "login@teste.com", "password": "senha123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "login@teste.com"
        assert data["token_type"] == "bearer"
        # Verifica que o token contem o email correto
        payload = jwt.decode(data["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "login@teste.com"

    def test_login_wrong_password(self, client: TestClient):
        """Senha incorreta deve retornar 401."""
        client.post(
            "/api/auth/register",
            json={"email": "wrong@teste.com", "password": "senha123"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "wrong@teste.com", "password": "senha_errada"},
        )
        assert response.status_code == 401
        assert "incorretos" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Email nao cadastrado deve retornar 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "ghost@teste.com", "password": "senha123"},
        )
        assert response.status_code == 401


class TestAuthMe:
    def test_me_authenticated(self, client: TestClient):
        """GET /api/auth/me com token valido deve retornar dados do usuario."""
        resp = client.post(
            "/api/auth/register",
            json={"email": "me@teste.com", "password": "senha123"},
        )
        token = resp.json()["access_token"]

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@teste.com"
        assert data["is_active"] is True

    def test_me_no_token(self, client: TestClient):
        """Requicao sem token deve retornar 401 ou 403 (dependendo do middleware HTTPBearer)."""
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 403)

    def test_me_invalid_token(self, client: TestClient):
        """Token invalido deve retornar 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer token_invalido"},
        )
        assert response.status_code == 401


class TestAuthLogout:
    def test_logout_authenticated(self, client: TestClient):
        """POST /api/auth/logout com token valido deve retornar 200."""
        resp = client.post(
            "/api/auth/register",
            json={"email": "logout@teste.com", "password": "senha123"},
        )
        token = resp.json()["access_token"]

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "sucesso" in response.json()["message"].lower()

    def test_logout_no_token(self, client: TestClient):
        """Logout sem token deve retornar 401 ou 403 (dependendo do middleware HTTPBearer)."""
        response = client.post("/api/auth/logout")
        assert response.status_code in (401, 403)