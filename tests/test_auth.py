from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient


SESSION_COOKIE_NAME = "__Host-session_token"


class TestSignup:
    def test_signup_success(self, client: TestClient):
        """Cadastro com dados validos deve retornar 200 e setar cookie."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "teste@example.com", "password": "senha12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "teste@example.com"
        assert "message" in data
        # Cookie de sessao deve estar presente
        cookies = response.cookies
        assert SESSION_COOKIE_NAME in cookies

    def test_signup_duplicate_email(self, client: TestClient):
        """Email duplicado deve retornar 409."""
        client.post(
            "/api/auth/signup",
            json={"email": "dup@example.com", "password": "senha12345"},
        )
        response = client.post(
            "/api/auth/signup",
            json={"email": "dup@example.com", "password": "outrasenha"},
        )
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"]

    def test_signup_short_password(self, client: TestClient):
        """Senha com menos de 8 caracteres deve ser rejeitada (422)."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "teste@example.com", "password": "curta"},
        )
        assert response.status_code == 422

    def test_signup_invalid_email(self, client: TestClient):
        """Email invalido deve ser rejeitado (422)."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "invalido", "password": "senha12345"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient):
        """Login com credenciais validas deve retornar 200 e setar cookie."""
        # Cadastra primeiro
        client.post(
            "/api/auth/signup",
            json={"email": "login@example.com", "password": "senha12345"},
        )
        # Login
        response = client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "senha12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "login@example.com"
        cookies = response.cookies
        assert SESSION_COOKIE_NAME in cookies

    def test_login_wrong_password(self, client: TestClient):
        """Senha incorreta deve retornar 401."""
        client.post(
            "/api/auth/signup",
            json={"email": "wrong@example.com", "password": "senha12345"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "wrong@example.com", "password": "senhaerrada"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        """Email nao cadastrado deve retornar 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "naoexiste@example.com", "password": "senha12345"},
        )
        assert response.status_code == 401


class TestMe:
    def test_me_authenticated(self, client: TestClient):
        """Usuario autenticado deve receber seus dados."""
        # Cadastra e login
        client.post(
            "/api/auth/signup",
            json={"email": "me@example.com", "password": "senha12345"},
        )
        # O cookie ja foi setado no cadastro, mas precisamos do valor
        signup_resp = client.post(
            "/api/auth/signup",
            json={"email": "me2@example.com", "password": "senha12345"},
        )
        cookie_value = signup_resp.cookies.get(SESSION_COOKIE_NAME)

        response = client.get(
            "/api/auth/me",
            cookies={SESSION_COOKIE_NAME: cookie_value},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me2@example.com"

    def test_me_unauthenticated(self, client: TestClient):
        """Sem cookie de sessao deve retornar 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client: TestClient):
        """Logout deve limpar o cookie e invalidar a sessao."""
        signup_resp = client.post(
            "/api/auth/signup",
            json={"email": "logout@example.com", "password": "senha12345"},
        )
        cookie_value = signup_resp.cookies.get(SESSION_COOKIE_NAME)

        # Logout
        response = client.post(
            "/api/auth/logout",
            cookies={SESSION_COOKIE_NAME: cookie_value},
        )
        assert response.status_code == 200

        # A sessao deve estar invalida
        me_response = client.get(
            "/api/auth/me",
            cookies={SESSION_COOKIE_NAME: cookie_value},
        )
        assert me_response.status_code == 401


class TestCSRFProtection:
    def test_request_without_csrf_header_blocked(self, client: TestClient):
        """Request sem X-Requested-With deve ser bloqueado para metodos inseguros."""
        # Remove o header CSRF padrao do conftest para testar a protecao
        client.headers.clear()
        response = client.post(
            "/api/auth/signup",
            json={"email": "csrf@example.com", "password": "senha12345"},
        )
        # Deve falhar por CSRF (403)
        assert response.status_code == 403

    def test_csrf_header_accepted(self, client: TestClient):
        """Request com X-Requested-With correto deve passar."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "csrfok@example.com", "password": "senha12345"},
        )
        assert response.status_code == 200