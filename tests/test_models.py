from __future__ import annotations

from datetime import datetime, timezone

from backend.models import ChatMessage, ChatSession, User


class TestUser:
    def test_create_user(self, db_session):
        user = User(email="user@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "user@teste.com"
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)


class TestChatSession:
    def test_create_session(self, db_session):
        user = User(email="session@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()

        session = ChatSession(user_id=user.id)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.user_id == user.id
        assert session.title is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_session_with_title(self, db_session):
        user = User(email="title@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()

        session = ChatSession(user_id=user.id, title="Minha Sessao")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.title == "Minha Sessao"

    def test_session_cascade_delete(self, db_session):
        """Deletar usuario deve deletar sessoes associadas."""
        user = User(email="cascade@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()

        session = ChatSession(user_id=user.id)
        db_session.add(session)
        db_session.commit()

        db_session.delete(user)
        db_session.commit()

        remaining = db_session.query(ChatSession).filter(ChatSession.user_id == user.id).all()
        assert len(remaining) == 0


class TestChatMessage:
    def test_create_message_defaults(self, db_session):
        """Deve criar uma mensagem com valores padrao."""
        user = User(email="msg@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()
        session = ChatSession(user_id=user.id)
        db_session.add(session)
        db_session.commit()

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

    def test_create_message_custom_model(self, db_session):
        """Deve criar uma mensagem com modelo customizado."""
        user = User(email="custom@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()
        session = ChatSession(user_id=user.id)
        db_session.add(session)
        db_session.commit()

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

    def test_query_by_session(self, db_session):
        """Deve filtrar mensagens por session_id."""
        user = User(email="query@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()
        s1 = ChatSession(user_id=user.id)
        s2 = ChatSession(user_id=user.id)
        db_session.add_all([s1, s2])
        db_session.commit()

        msg1 = ChatMessage(session_id=s1.id, role="user", content="a")
        msg2 = ChatMessage(session_id=s2.id, role="user", content="b")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        results = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.session_id == s1.id)
            .all()
        )
        assert len(results) == 1
        assert results[0].content == "a"

    def test_query_by_role(self, db_session):
        """Deve filtrar mensagens pelo campo role."""
        user = User(email="role@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()
        session = ChatSession(user_id=user.id)
        db_session.add(session)
        db_session.commit()

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

    def test_created_at_auto_set(self, db_session):
        """O campo created_at deve ser preenchido automaticamente com UTC now."""
        user = User(email="ts@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()
        session = ChatSession(user_id=user.id)
        db_session.add(session)
        db_session.commit()

        before = datetime.now(timezone.utc).replace(tzinfo=None)
        msg = ChatMessage(session_id=session.id, role="user", content="timestamp test")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert before <= msg.created_at <= after

    def test_content_persists_long_text(self, db_session):
        """Deve persistir conteudos longos corretamente."""
        user = User(email="long@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()
        session = ChatSession(user_id=user.id)
        db_session.add(session)
        db_session.commit()

        long_text = "Lorem ipsum " * 200
        msg = ChatMessage(session_id=session.id, role="user", content=long_text)
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.content == long_text

    def test_message_cascade_delete(self, db_session):
        """Deletar sessao deve deletar mensagens associadas."""
        user = User(email="casc@teste.com", password_hash="hash123")
        db_session.add(user)
        db_session.commit()
        session = ChatSession(user_id=user.id)
        db_session.add(session)
        db_session.commit()

        msg = ChatMessage(session_id=session.id, role="user", content="sera deletada")
        db_session.add(msg)
        db_session.commit()

        db_session.delete(session)
        db_session.commit()

        remaining = db_session.query(ChatMessage).filter(ChatMessage.session_id == session.id).all()
        assert len(remaining) == 0
