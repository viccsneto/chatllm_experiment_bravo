from __future__ import annotations

import bcrypt
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import JWT_ALGORITHM, JWT_SECRET_KEY
from backend.database import Base, get_db
from backend.main import app
from backend.models import User
from backend.routers.auth import get_current_user


TEST_USER_EMAIL = "test@exemplo.com"
TEST_USER_PASSWORD = "senha123"


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
def test_user(db_session):
    """Cria um usuario de teste no banco."""
    user = User(
        email=TEST_USER_EMAIL,
        password_hash=bcrypt.hashpw(TEST_USER_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_token(test_user):
    """Gera um token JWT valido para o usuario de teste."""
    from datetime import datetime, timedelta, timezone

    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode({"sub": test_user.email, "exp": expire}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@pytest.fixture
def auth_headers(user_token):
    """Retorna headers de autenticacao Bearer."""
    return {"Authorization": f"Bearer {user_token}"}


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
