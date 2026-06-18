"""Script de teste do fluxo completo JWT + sessoes + chat."""
import json
import sys
sys.path.insert(0, r"C:\Users\EyeTracker\Git\chatllm_experiment_bravo")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app

# Banco em memoria
test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(bind=test_engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# 1. Signup
r = client.post("/api/auth/signup", json={"email": "test@test.com", "password": "123456"})
print(f"1. SIGNUP: {r.status_code}")
assert r.status_code == 200, f"Signup failed: {r.json()}"
token = r.json()["token"]
print(f"   Token: {token[:40]}...")
assert token, "No token returned"

# 2. Fetch me
r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
print(f"2. FETCH ME: {r.status_code}")
assert r.status_code == 200, f"Fetch me failed: {r.json()}"

# 3. Create session
r = client.post("/api/sessions", json={}, headers={"Authorization": f"Bearer {token}"})
print(f"3. CREATE SESSION: {r.status_code}")
assert r.status_code == 201, f"Create session failed: {r.json()}"
session_id = r.json()["id"]
print(f"   Session ID: {session_id}")
print(f"   Title: {r.json()['title']}")

# 4. List sessions
r = client.get("/api/sessions", headers={"Authorization": f"Bearer {token}"})
print(f"4. LIST SESSIONS: {r.status_code}")
assert r.status_code == 200
assert len(r.json()["sessions"]) == 1
print(f"   Sessions count: {len(r.json()['sessions'])}")

# 5. Send message
r = client.post("/api/chat", json={"message": "Qual a capital do Brasil?", "session_id": session_id}, headers={"Authorization": f"Bearer {token}"})
print(f"5. SEND CHAT: {r.status_code}")
assert r.status_code in (200, 503), f"Chat failed: {r.json()}"

# 6. Get session detail
r = client.get(f"/api/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})
print(f"6. SESSION DETAIL: {r.status_code}")
assert r.status_code == 200
data = r.json()
print(f"   Title: {data['title']}")
print(f"   Messages count: {len(data['messages'])}")
if data["messages"]:
    print(f"   Messages:")
    for m in data["messages"]:
        print(f"      [{m['role']}] {m['content'][:60]}")

# 7. Auth isolation - access without token
r = client.get("/api/sessions", headers={})
print(f"7. NO AUTH: {r.status_code}")
assert r.status_code == 401

# 8. Auth isolation - invalid token
r = client.get("/api/sessions", headers={"Authorization": "Bearer invalidtoken"})
print(f"8. INVALID TOKEN: {r.status_code}")
assert r.status_code == 401

print("\n=== ALL TESTS PASSED ===")