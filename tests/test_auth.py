from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.config import AUTH_COOKIE_NAME
from backend.models import AuthSession, User
from backend.services.auth import hash_password, verify_password


VALID_CREDENTIALS = {
    "email": "usuario@example.com",
    "password": "senha-segura",
}


class TestPasswordHashing:
    def test_hash_does_not_store_plain_password(self):
        encoded = hash_password("senha-segura")
        assert "senha-segura" not in encoded
        assert encoded.startswith("scrypt$")

    def test_verify_password(self):
        encoded = hash_password("senha-segura")
        assert verify_password("senha-segura", encoded) is True
        assert verify_password("senha-errada", encoded) is False
        assert verify_password("senha-segura", "hash-invalido") is False


class TestRegister:
    def test_register_persists_user_and_starts_session(self, client, db_session):
        response = client.post("/api/auth/register", json=VALID_CREDENTIALS)

        assert response.status_code == 201
        assert response.json()["email"] == VALID_CREDENTIALS["email"]
        assert "password" not in response.json()
        assert client.cookies.get(AUTH_COOKIE_NAME)
        assert "httponly" in response.headers["set-cookie"].lower()

        user = db_session.query(User).one()
        assert user.email == VALID_CREDENTIALS["email"]
        assert user.password_hash != VALID_CREDENTIALS["password"]
        assert verify_password(VALID_CREDENTIALS["password"], user.password_hash)

        auth_session = db_session.query(AuthSession).one()
        assert auth_session.user_id == user.id
        assert auth_session.token_hash != client.cookies.get(AUTH_COOKIE_NAME)
        assert auth_session.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)

    def test_register_normalizes_email(self, client):
        response = client.post(
            "/api/auth/register",
            json={"email": "  Usuario@Example.COM ", "password": "senha-segura"},
        )
        assert response.status_code == 201
        assert response.json()["email"] == "usuario@example.com"

    def test_register_rejects_duplicate_email(self, client):
        first = client.post("/api/auth/register", json=VALID_CREDENTIALS)
        second = client.post("/api/auth/register", json=VALID_CREDENTIALS)
        assert first.status_code == 201
        assert second.status_code == 409

    def test_register_rejects_invalid_credentials(self, client):
        invalid_email = client.post(
            "/api/auth/register",
            json={"email": "email-invalido", "password": "senha-segura"},
        )
        short_password = client.post(
            "/api/auth/register",
            json={"email": "usuario@example.com", "password": "curta"},
        )
        assert invalid_email.status_code == 422
        assert short_password.status_code == 422


class TestLoginAndLogout:
    def test_login_with_valid_credentials(self, client):
        client.post("/api/auth/register", json=VALID_CREDENTIALS)
        client.post("/api/auth/logout")

        response = client.post("/api/auth/login", json=VALID_CREDENTIALS)

        assert response.status_code == 200
        assert response.json()["email"] == VALID_CREDENTIALS["email"]
        assert client.cookies.get(AUTH_COOKIE_NAME)

    def test_login_rejects_invalid_credentials(self, client):
        client.post("/api/auth/register", json=VALID_CREDENTIALS)
        client.post("/api/auth/logout")

        response = client.post(
            "/api/auth/login",
            json={**VALID_CREDENTIALS, "password": "senha-errada"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "E-mail ou senha invalidos."

    def test_me_returns_authenticated_user(self, client):
        client.post("/api/auth/register", json=VALID_CREDENTIALS)
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == VALID_CREDENTIALS["email"]

    def test_me_rejects_anonymous_user(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_logout_invalidates_session(self, client, db_session):
        client.post("/api/auth/register", json=VALID_CREDENTIALS)
        assert db_session.query(AuthSession).count() == 1

        logout_response = client.post("/api/auth/logout")
        me_response = client.get("/api/auth/me")

        assert logout_response.status_code == 204
        assert client.cookies.get(AUTH_COOKIE_NAME) is None
        assert db_session.query(AuthSession).count() == 0
        assert me_response.status_code == 401
