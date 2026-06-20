from __future__ import annotations

import json

import httpx

from backend.config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL_DEFAULT


_TITLE_PROMPT = (
    "You are a helpful assistant that generates short, descriptive titles for chat conversations. "
    "Based on the user's first message below, generate a concise title (maximum 8 words) in the "
    "same language as the message. Return ONLY the title as plain text, no quotes, no extra formatting."
)


async def generate_title(user_message: str) -> str:
    """
    Generate a short title for a chat session based on the first user message.
    Falls back to "Nova conversa" if the API call fails.
    """
    if not OPENROUTER_API_KEY:
        return "Nova conversa"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                json={
                    "model": OPENROUTER_MODEL_DEFAULT,
                    "messages": [
                        {"role": "system", "content": _TITLE_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": 30,
                    "temperature": 0.3,
                },
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "ChatLLM Experiment",
                },
            )

        if response.status_code >= 400:
            return "Nova conversa"

        data = response.json()
        title = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if title and len(title) > 100:
            title = title[:100]

        return title or "Nova conversa"

    except Exception:
        return "Nova conversa"