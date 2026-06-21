from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services.titling import generate_session_title


class TestGenerateSessionTitle:
    @pytest.mark.asyncio
    async def test_returns_title_on_success(self):
        """Deve retornar o titulo quando a API responde com sucesso."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Aprendendo Python"}}]
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.services.titling.OPENROUTER_API_KEY", "sk-test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                title = await generate_session_title(
                    user_message="O que e Python?",
                )
                assert title == "Aprendendo Python"

    @pytest.mark.asyncio
    async def test_returns_none_without_api_key(self):
        """Deve retornar None quando nao ha API key."""
        with patch("backend.services.titling.OPENROUTER_API_KEY", ""):
            title = await generate_session_title(
                user_message="Teste",
            )
            assert title is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        """Deve retornar None em caso de erro HTTP."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.services.titling.OPENROUTER_API_KEY", "sk-test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                title = await generate_session_title(
                    user_message="Teste",
                )
                assert title is None

    @pytest.mark.asyncio
    async def test_returns_none_on_request_error(self):
        """Deve retornar None em caso de erro de rede."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("No connection"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.services.titling.OPENROUTER_API_KEY", "sk-test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                title = await generate_session_title(
                    user_message="Teste",
                )
                assert title is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_response(self):
        """Deve retornar None quando a resposta vem vazia."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": ""}}]}

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.services.titling.OPENROUTER_API_KEY", "sk-test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                title = await generate_session_title(
                    user_message="Teste",
                )
                assert title is None