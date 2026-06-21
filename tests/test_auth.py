from __future__ import annotations

import pytest

from backend.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        """Deve hashear uma senha e verifica-la corretamente."""
        password = "minha_senha_segura_123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Deve rejeitar senha incorreta."""
        hashed = hash_password("senha_correta")
        assert verify_password("senha_errada", hashed) is False


class TestJWT:
    def test_create_and_decode(self):
        """Deve criar um token JWT e decodifica-lo, extraindo o email."""
        email = "teste@exemplo.com"
        token = create_access_token(email=email)
        assert token is not None
        decoded = decode_access_token(token)
        assert decoded == email

    def test_decode_invalid_token(self):
        """Deve retornar None para um token invalido."""
        assert decode_access_token("token_invalido") is None

    def test_decode_expired_token(self, monkeypatch):
        """Deve retornar None para um token expirado."""
        from datetime import datetime, timedelta, timezone
        from jose import jwt

        from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM

        # Criar token que ja expirou
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        token = jwt.encode(
            {"sub": "teste@exemplo.com", "exp": expire},
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        assert decode_access_token(token) is None

    def test_decode_token_without_sub(self, monkeypatch):
        """Deve retornar None para token sem o campo 'sub'."""
        from jose import jwt

        from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM

        token = jwt.encode(
            {"other": "data"},
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        assert decode_access_token(token) is None


class TestSignup:
    def test_signup_success(self, client):
        """Deve cadastrar um novo usuario e retornar token + email."""
        response = client.post("/api/signup", json={
            "email": "novo@teste.com",
            "password": "senha123",
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["email"] == "novo@teste.com"

    def test_signup_duplicate_email(self, client):
        """Deve retornar 409 ao tentar cadastrar email duplicado."""
        client.post("/api/signup", json={
            "email": "duplicado@teste.com",
            "password": "senha123",
        })
        response = client.post("/api/signup", json={
            "email": "duplicado@teste.com",
            "password": "outra_senha",
        })
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"].lower()

    def test_signup_invalid_email(self, client):
        """Deve retornar 422 para email invalido."""
        response = client.post("/api/signup", json={
            "email": "invalido",
            "password": "senha123",
        })
        assert response.status_code == 422

    def test_signup_short_password(self, client):
        """Deve retornar 422 para senha muito curta."""
        response = client.post("/api/signup", json={
            "email": "curta@teste.com",
            "password": "abc",
        })
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        """Deve fazer login com credenciais corretas e retornar token."""
        # Primeiro cadastra
        client.post("/api/signup", json={
            "email": "login@teste.com",
            "password": "senha123",
        })
        # Depois faz login
        response = client.post("/api/login", json={
            "email": "login@teste.com",
            "password": "senha123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "login@teste.com"

    def test_login_wrong_password(self, client):
        """Deve retornar 401 para senha incorreta."""
        client.post("/api/signup", json={
            "email": "wrong@teste.com",
            "password": "senha123",
        })
        response = client.post("/api/login", json={
            "email": "wrong@teste.com",
            "password": "senha_errada",
        })
        assert response.status_code == 401
        assert "incorretos" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Deve retornar 401 para usuario inexistente."""
        response = client.post("/api/login", json={
            "email": "naoexiste@teste.com",
            "password": "senha123",
        })
        assert response.status_code == 401


class TestGetMe:
    def test_get_me_authenticated(self, client):
        """Deve retornar dados do usuario com token valido."""
        signup_resp = client.post("/api/signup", json={
            "email": "me@teste.com",
            "password": "senha123",
        })
        token = signup_resp.json()["access_token"]

        response = client.get("/api/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@teste.com"
        assert "id" in data

    def test_get_me_no_token(self, client):
        """Deve retornar 401 sem token de acesso."""
        response = client.get("/api/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        """Deve retornar 401 com token invalido."""
        response = client.get("/api/me", headers={
            "Authorization": "Bearer token_invalido",
        })
        assert response.status_code == 401


class TestLogout:
    def test_logout_authenticated(self, client):
        """Deve retornar 204 ao fazer logout com token valido."""
        signup_resp = client.post("/api/signup", json={
            "email": "logout@teste.com",
            "password": "senha123",
        })
        token = signup_resp.json()["access_token"]

        response = client.post("/api/logout", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 204

    def test_logout_no_token(self, client):
        """Deve retornar 401 ao tentar logout sem token."""
        response = client.post("/api/logout")
        assert response.status_code == 401

    def test_logout_invalid_token(self, client):
        """Deve retornar 401 ao tentar logout com token invalido."""
        response = client.post("/api/logout", headers={
            "Authorization": "Bearer token_invalido",
        })
        assert response.status_code == 401