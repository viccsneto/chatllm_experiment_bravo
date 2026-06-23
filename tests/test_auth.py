from __future__ import annotations

from fastapi.testclient import TestClient


class TestSignup:
    def test_signup_success(self, client: TestClient):
        """Deve cadastrar um novo usuario e retornar token."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "teste@exemplo.com", "password": "senha123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_signup_duplicate_email(self, client: TestClient):
        """Email duplicado deve retornar 409."""
        client.post(
            "/api/auth/signup",
            json={"email": "dupe@exemplo.com", "password": "senha123"},
        )
        response = client.post(
            "/api/auth/signup",
            json={"email": "dupe@exemplo.com", "password": "outrasenha"},
        )
        assert response.status_code == 409
        assert "ja esta cadastrado" in response.json()["detail"]

    def test_signup_invalid_email(self, client: TestClient):
        """Email invalido deve retornar 422."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "invalido", "password": "senha123"},
        )
        assert response.status_code == 422

    def test_signup_short_password(self, client: TestClient):
        """Senha com menos de 6 caracteres deve retornar 422."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "teste@exemplo.com", "password": "12345"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient):
        """Login com credenciais corretas deve retornar token."""
        client.post(
            "/api/auth/signup",
            json={"email": "logintest@exemplo.com", "password": "senha123"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "logintest@exemplo.com", "password": "senha123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client: TestClient):
        """Senha incorreta deve retornar 401."""
        client.post(
            "/api/auth/signup",
            json={"email": "wrongpw@exemplo.com", "password": "senha123"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "wrongpw@exemplo.com", "password": "senhaerrada"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        """Email nao cadastrado deve retornar 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "naoexiste@exemplo.com", "password": "senha123"},
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout_returns_success(self, client: TestClient):
        """Logout deve retornar mensagem de sucesso."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestMe:
    def test_me_authenticated(self, client: TestClient):
        """Com token valido, deve retornar dados do usuario."""
        signup_resp = client.post(
            "/api/auth/signup",
            json={"email": "me@exemplo.com", "password": "senha123"},
        )
        token = signup_resp.json()["access_token"]

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@exemplo.com"
        assert "id" in data
        assert "created_at" in data

    def test_me_unauthenticated(self, client: TestClient):
        """Sem token, deve retornar 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client: TestClient):
        """Token invalido deve retornar 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer token-invalido"},
        )
        assert response.status_code == 401