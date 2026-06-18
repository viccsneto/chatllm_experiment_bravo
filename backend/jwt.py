from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from backend.config import JWT_ALGORITHM, JWT_SECRET_KEY, JWT_EXPIRATION_HOURS


def create_token(user_id: int) -> str:
    """Cria um JWT token para o usuario."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> int | None:
    """Verifica e decodifica um JWT token. Retorna user_id ou None se invalido."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        return int(user_id_str)
    except (JWTError, ValueError, TypeError):
        return None