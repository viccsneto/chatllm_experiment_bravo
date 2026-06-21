from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import SQLALCHEMY_DATABASE_URL, SQLITE_PATH


Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def run_migration():
    """Migra o schema do banco SQLite do formato da Tarefa 1 para o da Tarefa 2.

    A tabela chat_messages da Tarefa 1 tem:
      session_key VARCHAR(120) NOT NULL

    A Tarefa 2 substitui session_key por session_id + user_id (FKs), mas o SQLite
    legado mantém session_key como NOT NULL. Como SQLite ALTER TABLE não pode
    mudar constraints/DEFAULT, a estratégia é:

    1. Criar chat_sessions (nova)
    2. Criar chat_messages_v2 com schema correto (session_key nullable)
    3. Copiar dados + preencher session_id/user_id para registros órfãos
    4. Remover tabela antiga e renomear nova
    5. Recriar índices

    Seguro para rodar múltiplas vezes (idempotente).
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    existing_columns = {}
    if "chat_messages" in existing_tables:
        existing_columns["chat_messages"] = {
            col["name"] for col in inspector.get_columns("chat_messages")
        }

    # --- Passo 1: criar tabelas novas (chat_sessions, users se nao existir) ---
    Base.metadata.create_all(bind=engine)

    # --- Passo 2: detectar se a tabela chat_messages precisa ser migrada ---
    cols = existing_columns.get("chat_messages", set())
    already_migrated = "session_id" in cols

    # Se ja existe no schema novo (session_id presente), nada a fazer
    # mas precisamos garantir que session_key seja nullable no banco legado
    if already_migrated:
        # Verificar se session_key ainda e NOT NULL
        with engine.connect() as conn:
            table_info = conn.execute(
                text("PRAGMA table_info(chat_messages)")
            ).fetchall()
            for row in table_info:
                col_name, not_null = row[1], row[3]
                if col_name == "session_key" and not_null == 1:
                    # Precisa recriar a tabela para tornar nullable
                    _rebuild_chat_messages(conn)
                    return
        return  # Tudo ok, nada a fazer

    # --- Passo 3: migrar do schema antigo (com session_key) ---
    with engine.connect() as conn:
        _rebuild_chat_messages(conn)


def _rebuild_chat_messages(conn):
    """Recria chat_messages com session_key nullable, preservando dados."""
    # Backup dos dados existentes
    existing_rows = conn.execute(
        text("SELECT id, session_key, role, content, model, created_at FROM chat_messages")
    ).fetchall()

    # Drop da tabela antiga
    conn.execute(text("DROP TABLE IF EXISTS chat_messages"))

    # Criar tabela com schema novo (session_key nullable)
    conn.execute(text("""
        CREATE TABLE chat_messages (
            id INTEGER NOT NULL,
            session_id INTEGER NOT NULL REFERENCES chat_sessions(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            model VARCHAR(120),
            created_at DATETIME,
            session_key VARCHAR(120),
            PRIMARY KEY (id),
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """))
    conn.execute(text("CREATE INDEX ix_chat_messages_session_id ON chat_messages (session_id)"))
    conn.execute(text("CREATE INDEX ix_chat_messages_user_id ON chat_messages (user_id)"))
    conn.execute(text("CREATE INDEX ix_chat_messages_role ON chat_messages (role)"))
    conn.execute(text("CREATE INDEX ix_chat_messages_id ON chat_messages (id)"))
    conn.execute(text("CREATE INDEX ix_chat_messages_created_at ON chat_messages (created_at)"))
    conn.execute(text("CREATE INDEX ix_chat_messages_session_key ON chat_messages (session_key)"))
    conn.commit()

    # Se existem dados antigos, migrar
    if not existing_rows:
        return

    # Descobrir o primeiro usuario para associar mensagens orfas
    first_user = conn.execute(
        text("SELECT id FROM users ORDER BY id LIMIT 1")
    ).scalar()

    if not first_user:
        return  # Sem usuarios, dados orfos permanecerao sem dono

    # Criar uma sessao default para abrigar as mensagens orfas
    new_sid = conn.execute(
        text(
            "INSERT INTO chat_sessions (user_id, created_at, updated_at) "
            "VALUES (:uid, datetime('now'), datetime('now'))"
        ),
        {"uid": first_user},
    ).lastrowid
    conn.commit()

    # Reinserir todos os registros com session_id e user_id preenchidos
    for row in existing_rows:
        conn.execute(
            text("""
                INSERT INTO chat_messages
                    (id, session_id, user_id, role, content, model, created_at, session_key)
                VALUES (:id, :sid, :uid, :role, :content, :model, :created, :skey)
            """),
            {
                "id": row[0],
                "sid": new_sid,
                "uid": first_user,
                "role": row[2],
                "content": row[3],
                "model": row[4] or "google/gemma-4-31b-it",
                "created": row[5],
                "skey": row[1],
            },
        )
    conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
