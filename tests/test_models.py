from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.models import ChatMessage, ChatSession


@pytest.fixture
def session(db_session):
    """Cria uma ChatSession para usar nos testes de ChatMessage."""
    s = ChatSession(user_id=1, title="Test Session")
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


class TestChatMessage:
    def test_create_message_defaults(self, db_session, session):
        """Deve criar uma mensagem com valores padrao para model e created_at."""
        msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="Ola, mundo!",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.id is not None
        assert msg.session_id == session.id
        assert msg.role == "user"
        assert msg.content == "Ola, mundo!"
        assert msg.model == "google/gemma-4-31b-it"
        assert isinstance(msg.created_at, datetime)

    def test_create_message_custom_model(self, db_session, session):
        """Deve criar uma mensagem com modelo customizado."""
        msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="Teste",
            model="openai/gpt-4o",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.model == "openai/gpt-4o"

    def test_query_by_session_id(self, db_session, session):
        """Deve filtrar mensagens por session_id."""
        msg1 = ChatMessage(session_id=session.id, role="user", content="a")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="b")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        results = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .all()
        )
        assert len(results) == 2

    def test_query_by_role(self, db_session, session):
        """Deve filtrar mensagens pelo campo role."""
        msg1 = ChatMessage(session_id=session.id, role="user", content="pergunta")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="resposta")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        users = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.role == "user")
            .all()
        )
        assistants = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.role == "assistant")
            .all()
        )

        assert len(users) == 1
        assert len(assistants) == 1
        assert users[0].content == "pergunta"
        assert assistants[0].content == "resposta"

    def test_created_at_auto_set(self, db_session, session):
        """O campo created_at deve ser preenchido automaticamente com UTC now."""
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        msg = ChatMessage(session_id=session.id, role="user", content="timestamp test")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert before <= msg.created_at <= after

    def test_content_persists_long_text(self, db_session, session):
        """Deve persistir conteudos longos corretamente."""
        long_text = "Lorem ipsum " * 200
        msg = ChatMessage(session_id=session.id, role="user", content=long_text)
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.content == long_text

    def test_messages_ordered_by_created_at(self, db_session, session):
        """Mensagens devem ser ordenadas por created_at na relacao."""
        from datetime import timedelta

        base = datetime(2025, 1, 1, 12, 0, 0)
        msg1 = ChatMessage(session_id=session.id, role="user", content="first", created_at=base)
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="second", created_at=base + timedelta(seconds=1))
        db_session.add_all([msg1, msg2])
        db_session.commit()

        assert session.messages[0].content == "first"
        assert session.messages[1].content == "second"


class TestChatSession:
    def test_create_session_defaults(self, db_session):
        """Deve criar uma sessao com valores padrao."""
        s = ChatSession(user_id=1)
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        assert s.id is not None
        assert s.user_id == 1
        assert s.title == "New chat"
        assert isinstance(s.created_at, datetime)
        assert isinstance(s.updated_at, datetime)
        assert len(s.messages) == 0

    def test_session_with_messages(self, db_session):
        """Sessao deve relacionar mensagens corretamente."""
        s = ChatSession(user_id=1, title="Minha sessao")
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        msg1 = ChatMessage(session_id=s.id, role="user", content="Oi")
        msg2 = ChatMessage(session_id=s.id, role="assistant", content="Ola")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        assert len(s.messages) == 2

    def test_session_belongs_to_user(self, db_session):
        """Sessao deve estar associada a um usuario."""
        s1 = ChatSession(user_id=1)
        s2 = ChatSession(user_id=2)
        db_session.add_all([s1, s2])
        db_session.commit()

        from backend.models import User
        u1 = User(id=1, email="a@b.com", password_hash="x")
        u2 = User(id=2, email="c@d.com", password_hash="y")
        db_session.add_all([u1, u2])
        db_session.commit()

        assert s1.user_id == 1
        assert s2.user_id == 2
