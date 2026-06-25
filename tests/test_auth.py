from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from backend.models import Session, User


class TestSignup:
    def test_signup_success(self, client: TestClient, db_session):
        """Deve cadastrar um novo usuario e retornar token."""
        client.headers.clear()
        response = client.post(
            "/api/auth/signup",
            json={"email": "novo@teste.com", "password": "1234"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["email"] == "novo@teste.com"

    def test_signup_duplicate_email(self, client: TestClient, db_session):
        """Email duplicado deve retornar 409."""
        client.headers.clear()
        client.post("/api/auth/signup", json={"email": "dup@teste.com", "password": "1234"})
        response = client.post(
            "/api/auth/signup",
            json={"email": "dup@teste.com", "password": "5678"},
        )
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"]

    def test_signup_empty_password(self, client: TestClient):
        """Senha muito curta deve retornar 422."""
        client.headers.clear()
        response = client.post(
            "/api/auth/signup",
            json={"email": "teste@teste.com", "password": "12"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient, db_session):
        """Deve fazer login e retornar token."""
        # Primeiro cadastra
        client.headers.clear()
        client.post("/api/auth/signup", json={"email": "login@teste.com", "password": "1234"})

        # Depois login
        response = client.post(
            "/api/auth/login",
            json={"email": "login@teste.com", "password": "1234"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["email"] == "login@teste.com"

    def test_login_wrong_password(self, client: TestClient, db_session):
        """Senha errada deve retornar 401."""
        client.headers.clear()
        client.post("/api/auth/signup", json={"email": "wrong@teste.com", "password": "1234"})
        response = client.post(
            "/api/auth/login",
            json={"email": "wrong@teste.com", "password": "errada"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Usuario inexistente deve retornar 401."""
        client.headers.clear()
        response = client.post(
            "/api/auth/login",
            json={"email": "naoexiste@teste.com", "password": "1234"},
        )
        assert response.status_code == 401


class TestMe:
    def test_me_authenticated(self, client: TestClient, test_user):
        """Com token valido, deve retornar o email do usuario."""
        _, token = test_user
        response = client.get("/api/auth/me", headers={"token": token})
        assert response.status_code == 200
        assert response.json()["email"] == "teste@teste.com"

    def test_me_unauthenticated(self, client: TestClient):
        """Sem token, deve retornar 401."""
        response = client.get("/api/auth/me", headers={"token": ""})
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client: TestClient, test_user):
        """Deve fazer logout e invalidar o token."""
        _, token = test_user
        response = client.post("/api/auth/logout", headers={"token": token})
        assert response.status_code == 200
        assert response.json()["message"] == "Logout realizado com sucesso"

        # Token agora deve ser invalido
        response = client.get("/api/auth/me", headers={"token": token})
        assert response.status_code == 401

    def test_logout_invalid_token(self, client: TestClient):
        """Token inexistente deve retornar 200 (idempotente)."""
        response = client.post(
            "/api/auth/logout",
            headers={"token": "token_inexistente"},
        )
        assert response.status_code == 200