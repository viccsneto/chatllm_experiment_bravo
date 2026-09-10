from __future__ import annotations

from backend.services.titles import TITLE_MAX_LENGTH, derive_session_title


class TestDeriveSessionTitle:
    def test_uses_first_user_message(self):
        title = derive_session_title(
            "Como criar uma API com FastAPI?",
            "Voce pode comecar criando uma rota.",
        )
        assert title == "Como criar uma API com FastAPI?"

    def test_normalizes_markdown_and_whitespace(self):
        title = derive_session_title("  ## Aprender   **Python**\ncom exemplos  ")
        assert title == "Aprender Python com exemplos"

    def test_limits_long_titles_at_a_word_boundary(self):
        title = derive_session_title("palavra " * 20)
        assert len(title) <= TITLE_MAX_LENGTH
        assert title.endswith("…")

    def test_has_fallback_for_empty_context(self):
        assert derive_session_title("", "") == "Nova conversa"
