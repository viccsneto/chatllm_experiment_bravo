from __future__ import annotations

import os

# Define JWT_SECRET_KEY antes de qualquer import que carregue backend.config
os.environ.setdefault("JWT_SECRET_KEY", "test-key-nao-use-em-producao")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app


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
def auth_token(client):
    """Cadastra um usuario de teste e retorna um token JWT valido."""
    response = client.post("/api/signup", json={
        "email": "teste@chat.com",
        "password": "senha123",
    })
    assert response.status_code == 201
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Retorna headers de Authorization com token valido."""
    return {"Authorization": f"Bearer {auth_token}"}
