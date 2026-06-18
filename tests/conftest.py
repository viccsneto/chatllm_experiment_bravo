from __future__ import annotations

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import User


@pytest.fixture(scope="session")
def engine():
    """Cria um engine SQLite em memoria para os testes."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="session")
def tables(engine):
    """Cria todas as tabelas antes dos testes e as remove ao final."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine, tables):
    """Retorna uma sessao de banco limpa para cada teste.

    Usa transacao aninhada (SAVEPOINT) para isolar cada teste.
    Ao final do teste, o rollback desfaz todas as alteracoes.
    """
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """Retorna um TestClient do FastAPI com o banco de testes injetado."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client, db_session):
    """Retorna um TestClient autenticado com um usuario criado.

    Cria um usuario de teste, faz login e retorna (client, token).
    """
    hashed = bcrypt.hashpw("secret123".encode("utf-8"), bcrypt.gensalt())
    user = User(
        email="test@example.com",
        password_hash=hashed.decode("utf-8"),
    )
    db_session.add(user)
    db_session.commit()

    response = client.post("/api/auth/login", json={"email": "test@example.com", "password": "secret123"})
    assert response.status_code == 200
    token = response.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client

    response = client.post("/api/auth/login", json={"email": "test@example.com", "password": "secret123"})
    assert response.status_code == 200
    return client
