from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestSessionsAPI:
    def test_list_sessions_requires_auth(self, client: TestClient):
        """Sem autenticacao, listar sessoes deve retornar 401."""
        response = client.get("/api/sessions")
        assert response.status_code == 401

    def test_create_session(self, authed_client):
        """Criar uma sessao deve retornar 201 com dados validos."""
        client, _ = authed_client
        response = client.post("/api/sessions", json={})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Nova conversa"
        assert "id" in data

    def test_list_sessions_after_create(self, authed_client):
        """Listar sessoes deve incluir a sessao criada."""
        client, _ = authed_client
        client.post("/api/sessions", json={})
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) >= 1

    def test_list_sessions_ordered_by_recent(self, authed_client):
        """Sessoes devem vir ordenadas da mais recente para a mais antiga."""
        client, _ = authed_client
        s1 = client.post("/api/sessions", json={}).json()
        import time
        time.sleep(0.01)
        s2 = client.post("/api/sessions", json={}).json()

        response = client.get("/api/sessions")
        sessions = response.json()["sessions"]
        # A mais recente (s2) deve vir primeiro
        assert sessions[0]["id"] == s2["id"]
        assert sessions[1]["id"] == s1["id"]

    def test_get_messages_empty_session(self, authed_client):
        """Sessao vazia deve retornar lista vazia de mensagens."""
        client, session_id = authed_client
        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["messages"] == []

    def test_get_messages_nonexistent_session(self, authed_client):
        """Sessao inexistente deve retornar 404."""
        client, _ = authed_client
        response = client.get("/api/sessions/99999/messages")
        assert response.status_code == 404

    def test_cannot_access_other_user_session(self, client, db_session):
        """Um usuario nao pode acessar sessoes de outro usuario."""
        from backend.models import User, ChatSession, Session as AuthSession
        from datetime import datetime, timedelta, timezone
        import secrets

        # Cria usuario 1 com sessao
        user1 = User(email="user1@test.com", hashed_password="hash")
        db_session.add(user1)
        db_session.commit()

        cs = ChatSession(user_id=user1.id, title="Sessao do user1")
        db_session.add(cs)
        db_session.commit()

        # Cria usuario 2 e autentica como ele
        user2 = User(email="user2@test.com", hashed_password="hash")
        db_session.add(user2)
        db_session.commit()

        token = secrets.token_urlsafe(48)
        auth_sess = AuthSession(
            user_id=user2.id, token=token,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=8),
        )
        db_session.add(auth_sess)
        db_session.commit()

        client.cookies.set("__Host-session_token", token)

        # Tenta acessar a sessao do user1
        response = client.get(f"/api/sessions/{cs.id}/messages")
        assert response.status_code == 404

    def test_update_title_once(self, authed_client):
        """Titulo so deve ser atualizado se ainda for 'Nova conversa'."""
        client, session_id = authed_client
        # Atualiza titulo
        response = client.put(
            f"/api/sessions/{session_id}/title",
            json={"title": "Meu Chat"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Meu Chat"

        # Segunda tentativa nao deve mudar (ja foi alterado)
        response = client.put(
            f"/api/sessions/{session_id}/title",
            json={"title": "Outro Titulo"},
        )
        assert response.json()["title"] == "Meu Chat"

    def test_update_title_empty_ignored(self, authed_client):
        """Titulo vazio nao deve ser aplicado."""
        client, session_id = authed_client
        response = client.put(
            f"/api/sessions/{session_id}/title",
            json={"title": ""},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Nova conversa"


class TestSessionIsolation:
    def test_messages_per_session(self, authed_client):
        """Mensagens de uma sessao nao devem aparecer em outra."""
        client, _ = authed_client
        s1 = client.post("/api/sessions", json={}).json()
        s2 = client.post("/api/sessions", json={}).json()

        # Nao podemos testar o chat real (sem API key), mas verificamos
        # que cada sessao comeca vazia
        m1 = client.get(f"/api/sessions/{s1['id']}/messages").json()
        m2 = client.get(f"/api/sessions/{s2['id']}/messages").json()
        assert len(m1["messages"]) == 0
        assert len(m2["messages"]) == 0