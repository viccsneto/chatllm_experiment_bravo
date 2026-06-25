from __future__ import annotations

import hashlib
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import AuthSession as DbSession
from backend.models import User


def _fake_token():
    return hashlib.sha256(os.urandom(32)).hexdigest()


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
def test_user(db_session):
    """Cria um usuario de teste e retorna (user, token)."""
    user = User(email="teste@teste.com", password_hash=hashlib.sha256(b"1234").hexdigest())
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = _fake_token()
    db_session.add(DbSession(user_id=user.id, token=token))
    db_session.commit()

    return user, token


@pytest.fixture
def client(db_session, test_user):
    """Retorna um TestClient do FastAPI com o banco de testes injetado."""
    _, token = test_user

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        test_client.headers["token"] = token
        yield test_client

    app.dependency_overrides.clear()
