from __future__ import annotations

from datetime import datetime, timezone

from backend.models import ChatMessage, Session


class TestSession:
    def test_create_session_defaults(self, db_session, test_user):
        """Deve criar uma sessao com valores padrao."""
        session = Session(user_id=test_user.id)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.title is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_session_title(self, db_session, test_user):
        """Deve criar uma sessao com titulo."""
        session = Session(user_id=test_user.id, title="Meu titulo")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.title == "Meu titulo"

    def test_query_sessions_by_user(self, db_session, test_user):
        """Deve filtrar sessoes por usuario."""
        s1 = Session(user_id=test_user.id)
        s2 = Session(user_id=test_user.id)
        db_session.add_all([s1, s2])
        db_session.commit()

        results = db_session.query(Session).filter(Session.user_id == test_user.id).all()
        assert len(results) == 2


class TestChatMessage:
    def test_create_message_defaults(self, db_session, test_user, test_session):
        """Deve criar uma mensagem com valores padrao."""
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

    def test_query_by_session_id(self, db_session, test_user, test_session):
        """Deve filtrar mensagens por session_id."""
        s2 = Session(user_id=test_user.id)
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

        users = db_session.query(ChatMessage).filter(ChatMessage.role == "user").all()
        assistants = db_session.query(ChatMessage).filter(ChatMessage.role == "assistant").all()

        assert len(users) == 1
        assert len(assistants) == 1

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
