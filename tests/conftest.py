from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import ChatSession, User


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
    """Retorna uma sessao de banco limpa para cada teste."""
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
    """Retorna um TestClient com banco injetado e header CSRF."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        test_client.headers["X-Requested-With"] = "XMLHttpRequest"
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def authed_client(client, db_session):
    """Retorna um TestClient ja autenticado, com uma sessao de chat criada."""
    from backend.models import Session as AuthSession
    from backend.models import User, ChatSession
    from datetime import datetime, timedelta, timezone
    import secrets

    user = User(email="test@example.com", hashed_password="$2b$12$dummyhashdummyhashdummyhashdummyhashdummyhashdummyha")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    chat_session = ChatSession(user_id=user.id, title="Nova conversa")
    db_session.add(chat_session)
    auth_session = AuthSession(
        user_id=user.id,
        token=secrets.token_urlsafe(48),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=8),
    )
    db_session.add(auth_session)
    db_session.commit()
    db_session.refresh(chat_session)

    client.cookies.set("__Host-session_token", auth_session.token)
    return client, chat_session.id
