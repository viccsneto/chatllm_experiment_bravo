from __future__ import annotations

import re


TITLE_MAX_LENGTH = 60


def derive_session_title(user_message: str, assistant_reply: str = "") -> str:
    """Cria um titulo curto e deterministico a partir do primeiro contexto util."""
    source = user_message.strip() or assistant_reply.strip() or "Nova conversa"
    normalized = re.sub(r"[`#*_]+", "", source)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if len(normalized) <= TITLE_MAX_LENGTH:
        return normalized

    available = normalized[: TITLE_MAX_LENGTH - 1].rstrip()
    if " " in available:
        available = available.rsplit(" ", 1)[0]
    return f"{available.rstrip('.,;:-')}…"
