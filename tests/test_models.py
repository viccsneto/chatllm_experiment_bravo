from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.models import ChatMessage, ChatSession, User
from backend.services.auth import hash_password


@pytest.fixture
def test_user(db_session):
    user = User(email="model-test@teste.com", hashed_password=hash_password("senha123"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_session(db_session, test_user):
    session = ChatSession(user_id=test_user.id)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


class TestChatMessage:
    def test_create_message_defaults(self, db_session, test_user, test_session):
        """Deve criar uma mensagem com valores padrao para role, model e created_at."""
        msg = ChatMessage(
            session_id=test_session.id,
            user_id=test_user.id,
            role="user",
            content="Ola, mundo!",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.id is not None
        assert msg.session_id == test_session.id
        assert msg.user_id == test_user.id
        assert msg.role == "user"
        assert msg.content == "Ola, mundo!"
        assert msg.model == "google/gemma-4-31b-it"
        assert isinstance(msg.created_at, datetime)

    def test_create_message_custom_model(self, db_session, test_user, test_session):
        """Deve criar uma mensagem com modelo customizado."""
        msg = ChatMessage(
            session_id=test_session.id,
            user_id=test_user.id,
            role="user",
            content="Teste",
            model="openai/gpt-4o",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.model == "openai/gpt-4o"

    def test_query_by_session(self, db_session, test_user, test_session):
        """Deve filtrar mensagens por session_id."""
        s2 = ChatSession(user_id=test_user.id)
        db_session.add(s2)
        db_session.commit()

        msg1 = ChatMessage(session_id=test_session.id, user_id=test_user.id, role="user", content="a")
        msg2 = ChatMessage(session_id=s2.id, user_id=test_user.id, role="user", content="b")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        results = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.session_id == test_session.id)
            .all()
        )
        assert len(results) == 1
        assert results[0].content == "a"

    def test_query_by_role(self, db_session, test_user, test_session):
        """Deve filtrar mensagens pelo campo role."""
        msg1 = ChatMessage(session_id=test_session.id, user_id=test_user.id, role="user", content="pergunta")
        msg2 = ChatMessage(session_id=test_session.id, user_id=test_user.id, role="assistant", content="resposta")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        users = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.role == "user")
            .all()
        )
        assert len(users) == 1
        assert users[0].content == "pergunta"

    def test_created_at_auto_set(self, db_session, test_user, test_session):
        """O campo created_at deve ser preenchido automaticamente com UTC now."""
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        msg = ChatMessage(session_id=test_session.id, user_id=test_user.id, role="user", content="timestamp test")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert before <= msg.created_at <= after

    def test_content_persists_long_text(self, db_session, test_user, test_session):
        """Deve persistir conteudos longos corretamente."""
        long_text = "Lorem ipsum " * 200
        msg = ChatMessage(session_id=test_session.id, user_id=test_user.id, role="user", content=long_text)
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.content == long_text
