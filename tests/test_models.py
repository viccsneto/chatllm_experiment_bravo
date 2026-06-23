from __future__ import annotations

from datetime import datetime, timezone

from backend.models import ChatMessage, ChatSession, User


class TestUser:
    def test_create_user(self, db_session):
        user = User(email="user@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.id is not None
        assert user.email == "user@test.com"
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)


class TestChatSession:
    def test_create_session_default_title(self, db_session):
        user = User(email="sess@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        cs = ChatSession(user_id=user.id)
        db_session.add(cs)
        db_session.commit()
        db_session.refresh(cs)

        assert cs.id is not None
        assert cs.title == "Nova conversa"
        assert cs.user_id == user.id
        assert isinstance(cs.created_at, datetime)
        assert isinstance(cs.updated_at, datetime)

    def test_session_belongs_to_user(self, db_session):
        user = User(email="sess2@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        cs = ChatSession(user_id=user.id, title="Meu Chat")
        db_session.add(cs)
        db_session.commit()

        assert cs in user.chat_sessions


class TestChatMessage:
    def test_create_message_requires_session(self, db_session):
        user = User(email="msg@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        cs = ChatSession(user_id=user.id)
        db_session.add(cs)
        db_session.commit()
        db_session.refresh(cs)

        msg = ChatMessage(
            session_id=cs.id,
            role="user",
            content="Ola, mundo!",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.id is not None
        assert msg.session_id == cs.id
        assert msg.role == "user"
        assert msg.content == "Ola, mundo!"
        assert msg.model == "google/gemma-4-31b-it"
        assert isinstance(msg.created_at, datetime)

    def test_message_in_session_relationship(self, db_session):
        user = User(email="rel@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        cs = ChatSession(user_id=user.id)
        db_session.add(cs)
        db_session.commit()
        db_session.refresh(cs)

        msg1 = ChatMessage(session_id=cs.id, role="user", content="msg1")
        msg2 = ChatMessage(session_id=cs.id, role="assistant", content="msg2")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        assert len(cs.messages) == 2
        assert cs.messages[0].content == "msg1"
        assert cs.messages[1].content == "msg2"

    def test_query_by_session_id(self, db_session):
        user = User(email="qry@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        cs1 = ChatSession(user_id=user.id)
        cs2 = ChatSession(user_id=user.id)
        db_session.add_all([cs1, cs2])
        db_session.commit()
        db_session.refresh(cs1)
        db_session.refresh(cs2)

        msg1 = ChatMessage(session_id=cs1.id, role="user", content="a")
        msg2 = ChatMessage(session_id=cs2.id, role="user", content="b")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        results = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.session_id == cs1.id)
            .all()
        )
        assert len(results) == 1
        assert results[0].content == "a"

    def test_query_by_role(self, db_session):
        user = User(email="role@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        cs = ChatSession(user_id=user.id)
        db_session.add(cs)
        db_session.commit()
        db_session.refresh(cs)

        msg1 = ChatMessage(session_id=cs.id, role="user", content="pergunta")
        msg2 = ChatMessage(session_id=cs.id, role="assistant", content="resposta")
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
        user = User(email="time@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        cs = ChatSession(user_id=user.id)
        db_session.add(cs)
        db_session.commit()
        db_session.refresh(cs)

        msg = ChatMessage(session_id=cs.id, role="user", content="teste")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert isinstance(msg.created_at, datetime)
        assert msg.created_at <= datetime.now(timezone.utc).replace(tzinfo=None)

    def test_content_persists_long_text(self, db_session):
        user = User(email="long@test.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        cs = ChatSession(user_id=user.id)
        db_session.add(cs)
        db_session.commit()
        db_session.refresh(cs)

        long_text = "Lorem ipsum " * 100
        msg = ChatMessage(session_id=cs.id, role="user", content=long_text)
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert len(msg.content) > 500

    def test_created_at_auto_set(self, db_session):
        """O campo created_at deve ser preenchido automaticamente com UTC now."""
        user = User(email="ts@test.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()
        cs = ChatSession(user_id=user.id)
        db_session.add(cs)
        db_session.commit()
        db_session.refresh(cs)

        before = datetime.now(timezone.utc).replace(tzinfo=None)
        msg = ChatMessage(session_id=cs.id, role="user", content="timestamp test")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert before <= msg.created_at <= after
