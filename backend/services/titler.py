from __future__ import annotations

import re

from backend.config import OPENROUTER_API_KEY, OPENROUTER_MODEL_DEFAULT
from backend.services.openrouter import OpenRouterConfigError, generate_reply


_TITLE_SYSTEM_PROMPT = (
    "You generate concise chat titles (max 6 words). "
    "Given a conversation's first exchange, respond ONLY with the title "
    "in plain text — no quotes, no punctuation, no labels like 'Title:'."
)


_FALLBACK_CHARS = 45


def _fallback_title(user_message: str) -> str:
    title = user_message.strip().split("\n")[0][:_FALLBACK_CHARS].strip()
    if not title:
        return "Nova conversa"
    if len(title) > _FALLBACK_CHARS - 3:
        title = title[:_FALLBACK_CHARS - 3] + "..."
    return title


async def generate_title(user_message: str, assistant_reply: str) -> str:
    """Gera um titulo conciso (max 6 palavras) via OpenRouter.

    Envia apenas o conteudo real da conversa (sem labels como 'User message:')
    para evitar que o modelo os repita. Se falhar, usa fallback local.
    """
    if not OPENROUTER_API_KEY:
        return _fallback_title(user_message)

    context = f"{user_message}\n\n{assistant_reply}"

    try:
        title, _ = await generate_reply(
            user_message=context,
            history=[],
            model=OPENROUTER_MODEL_DEFAULT,
            system_prompt=_TITLE_SYSTEM_PROMPT,
        )
        title = title.strip().strip('"').strip("'").strip('"').strip("'").strip()
        # Remove "Title:" ou "Título:" se o modelo ignorar o prompt
        title = re.sub(r'^(?:Title|Título|Topic|Assunto)\s*[:\-]?\s*', '', title, flags=re.IGNORECASE).strip()
        # Remove pontuacao final
        title = re.sub(r'[.!?:;]+$', '', title).strip()
        if len(title) > 60:
            title = title[:57] + "..."
        if not title or len(title) < 3:
            return _fallback_title(user_message)
        return title
    except (OpenRouterConfigError, RuntimeError):
        return _fallback_title(user_message)