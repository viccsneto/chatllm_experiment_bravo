from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import SQLALCHEMY_DATABASE_URL, SQLITE_PATH


Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def initialize_database() -> None:
    """Cria o schema e aplica a pequena migracao necessaria ao banco do MVP."""
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "chat_messages" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("chat_messages")}
    if "session_id" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE chat_messages "
                    "ADD COLUMN session_id INTEGER REFERENCES chat_sessions(id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id "
                    "ON chat_messages (session_id)"
                )
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
