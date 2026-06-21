from __future__ import annotations

import json

import httpx

from backend.config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL_DEFAULT


_TITLE_PROMPT = (
    "Based on the user's first message, generate a short, descriptive title "
    "(maximum 6 words) in Portuguese for this conversation.\n"
    "Respond with ONLY the title, no quotes, no punctuation, no extra text.\n\n"
    "User message: {user_message}"
)


async def generate_session_title(*, user_message: str) -> str | None:
    """Gera um titulo curto para a sessao usando o OpenRouter.

    Retorna o titulo ou None em caso de falha (rede, API, parsing).
    Nunca levanta excecao — o chamador deve tratar None como fallback.
    """
    if not OPENROUTER_API_KEY:
        return None

    prompt = _TITLE_PROMPT.format(
        user_message=user_message.strip()[:300],
    )

    payload = {
        "model": OPENROUTER_MODEL_DEFAULT,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 30,
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "ChatLLM Experiment",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)

        if response.status_code >= 400:
            return None

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        title = content.strip().strip('"').strip("'")[:120]
        return title if title else None
    except (httpx.RequestError, json.JSONDecodeError, KeyError, IndexError):
        return None