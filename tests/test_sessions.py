from __future__ import annotations

from fastapi.testclient import TestClient


class TestSessionsAPI:
    def test_list_sessions_requires_auth(self, client: TestClient):
        response = client.get("/api/sessions")
        assert response.status_code == 401

    def test_create_session_requires_auth(self, client: TestClient):
        response = client.post("/api/sessions", json={})
        assert response.status_code == 401

    def test_create_and_list_sessions(self, client: TestClient, auth_headers):
        # Create first session
        resp1 = client.post("/api/sessions", json={}, headers=auth_headers)
        assert resp1.status_code == 201
        data1 = resp1.json()
        assert data1["title"] == "Nova conversa"
        assert data1["id"] is not None

        # Create second session
        resp2 = client.post("/api/sessions", json={}, headers=auth_headers)
        assert resp2.status_code == 201
        data2 = resp2.json()

        # List sessions (most recent first)
        resp_list = client.get("/api/sessions", headers=auth_headers)
        assert resp_list.status_code == 200
        data = resp_list.json()
        assert len(data["sessions"]) == 2
        # Most recent should be first
        assert data["sessions"][0]["id"] == data2["id"]

    def test_get_session(self, client: TestClient, auth_headers):
        create_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = create_resp.json()["id"]

        resp = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id

    def test_get_session_not_found(self, client: TestClient, auth_headers):
        resp = client.get("/api/sessions/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_session(self, client: TestClient, auth_headers):
        create_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = create_resp.json()["id"]

        resp = client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
        assert resp.status_code == 204

        # Verify it's gone
        resp_get = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert resp_get.status_code == 404

    def test_delete_session_not_found(self, client: TestClient, auth_headers):
        resp = client.delete("/api/sessions/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_sessions_isolated_per_user(self, client: TestClient, auth_headers):
        """Sessoes de um usuario nao devem ser visiveis para outro."""
        # Create session for user 1
        client.post("/api/sessions", json={}, headers=auth_headers)

        # Register and login as user 2
        client.post("/api/auth/register", json={"email": "user2@teste.com", "password": "123456"})
        resp_login = client.post("/api/auth/login", json={"email": "user2@teste.com", "password": "123456"})
        token2 = resp_login.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        resp_list = client.get("/api/sessions", headers=headers2)
        assert resp_list.status_code == 200
        assert len(resp_list.json()["sessions"]) == 0