from __future__ import annotations

from backend.config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL_DEFAULT
from backend.services.openrouter import build_headers


def _fallback_title(user_message: str) -> str:
    """Gera um titulo local extraindo as primeiras palavras da mensagem."""
    cleaned = user_message.strip()[:80]
    words = cleaned.split()
    # Pega ate 6 palavras
    title = " ".join(words[:6])
    if len(title) > 70:
        title = title[:70]
    if not title:
        return "Nova conversa"
    return title


async def generate_session_title(user_message: str) -> str:
    """Gera um titulo curto para a sessao baseado na primeira mensagem do usuario.
    Tenta usar OpenRouter primeiro; se falhar, usa fallback local."""
    # Tentativa via OpenRouter
    if OPENROUTER_API_KEY:
        try:
            import httpx

            system_prompt = (
                "You are a title generator. Based on the user's first message in a chat session, "
                "generate a very short title (maximum 6 words) that summarizes the conversation topic. "
                "Respond with ONLY the title, no quotes, no punctuation, no explanation."
            )

            payload = {
                "model": OPENROUTER_MODEL_DEFAULT,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 20,
                "temperature": 0.3,
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(OPENROUTER_API_URL, json=payload, headers=build_headers())
            if response.status_code < 400:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                title = content.strip().strip('"').strip("'")
                if title:
                    return title[:255]
        except Exception:
            pass

    # Fallback local
    return _fallback_title(user_message)