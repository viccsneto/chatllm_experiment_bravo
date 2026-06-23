from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import User


class TestRegister:
    def test_register_success(self, client: TestClient, db_session: Session):
        """Deve cadastrar um novo usuario e retornar token."""
        response = client.post(
            "/api/auth/register",
            json={"email": "novo@teste.com", "password": "123456"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verificar que o usuario foi criado no banco
        user = db_session.query(User).filter(User.email == "novo@teste.com").first()
        assert user is not None
        assert user.email == "novo@teste.com"

    def test_register_duplicate_email(self, client: TestClient):
        """Email duplicado deve retornar 409."""
        client.post(
            "/api/auth/register",
            json={"email": "dup@teste.com", "password": "123456"},
        )
        response = client.post(
            "/api/auth/register",
            json={"email": "dup@teste.com", "password": "123456"},
        )
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"]

    def test_register_short_password(self, client: TestClient):
        """Senha com menos de 6 caracteres deve retornar 422."""
        response = client.post(
            "/api/auth/register",
            json={"email": "short@teste.com", "password": "123"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient, auth_headers):
        """Deve fazer login e retornar token."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "123456"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient):
        """Senha incorreta deve retornar 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )
        assert response.status_code == 401
        assert "incorretos" in response.json()["detail"]

    def test_login_nonexistent_email(self, client: TestClient):
        """Email nao cadastrado deve retornar 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "naoexiste@teste.com", "password": "123456"},
        )
        assert response.status_code == 401


class TestMe:
    def test_me_success(self, client: TestClient, auth_headers):
        """Deve retornar dados do usuario autenticado."""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "is_active" in data

    def test_me_without_token(self, client: TestClient):
        """Sem token deve retornar 403."""
        response = client.get("/api/auth/me")
        assert response.status_code == 403

    def test_me_with_invalid_token(self, client: TestClient):
        """Token invalido deve retornar 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer token-invalido"},
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client: TestClient, auth_headers):
        """Logout deve retornar mensagem de sucesso."""
        response = client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Logout realizado com sucesso."

    def test_logout_without_token(self, client: TestClient):
        """Logout sem token deve retornar 403."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 403