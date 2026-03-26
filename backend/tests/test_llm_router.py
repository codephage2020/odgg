"""Tests for LLM router — model string building and API params."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from odgg.services.llm_router import _build_model_string, _get_api_params


class TestBuildModelString:
    @patch("odgg.services.llm_router.settings")
    def test_openai_provider(self, mock_settings):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_model = "gpt-4o"
        assert _build_model_string() == "gpt-4o"

    @patch("odgg.services.llm_router.settings")
    def test_ollama_provider(self, mock_settings):
        mock_settings.llm_provider = "ollama"
        mock_settings.llm_model = "llama3.1"
        assert _build_model_string() == "ollama/llama3.1"

    @patch("odgg.services.llm_router.settings")
    def test_anthropic_provider(self, mock_settings):
        mock_settings.llm_provider = "anthropic"
        mock_settings.llm_model = "claude-3-sonnet"
        assert _build_model_string() == "anthropic/claude-3-sonnet"


class TestGetApiParams:
    @patch("odgg.services.llm_router.settings")
    def test_with_api_key(self, mock_settings):
        mock_settings.llm_api_key = "sk-test123"
        mock_settings.llm_base_url = ""
        params = _get_api_params()
        assert params["api_key"] == "sk-test123"
        assert "api_base" not in params

    @patch("odgg.services.llm_router.settings")
    def test_with_base_url(self, mock_settings):
        mock_settings.llm_api_key = ""
        mock_settings.llm_base_url = "http://localhost:11434"
        params = _get_api_params()
        assert params["api_base"] == "http://localhost:11434"
        assert "api_key" not in params

    @patch("odgg.services.llm_router.settings")
    def test_both_params(self, mock_settings):
        mock_settings.llm_api_key = "sk-key"
        mock_settings.llm_base_url = "http://localhost:11434"
        params = _get_api_params()
        assert "api_key" in params
        assert "api_base" in params

    @patch("odgg.services.llm_router.settings")
    def test_no_params(self, mock_settings):
        mock_settings.llm_api_key = ""
        mock_settings.llm_base_url = ""
        params = _get_api_params()
        assert params == {}


class TestChatCompletion:
    @patch("odgg.services.llm_router.litellm")
    @patch("odgg.services.llm_router.settings")
    async def test_returns_parsed_json(self, mock_settings, mock_litellm):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_model = "gpt-4o"
        mock_settings.llm_api_key = "sk-test"
        mock_settings.llm_base_url = ""
        mock_settings.llm_timeout = 30

        # Mock the response
        mock_choice = MagicMock()
        mock_choice.message.content = '{"result": "test"}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        from odgg.services.llm_router import chat_completion

        result = await chat_completion([{"role": "user", "content": "test"}])
        assert result == {"result": "test"}

    @patch("odgg.services.llm_router.litellm")
    @patch("odgg.services.llm_router.settings")
    async def test_non_json_returns_content(self, mock_settings, mock_litellm):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_model = "gpt-4o"
        mock_settings.llm_api_key = "sk-test"
        mock_settings.llm_base_url = ""
        mock_settings.llm_timeout = 30

        mock_choice = MagicMock()
        mock_choice.message.content = "just plain text"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        from odgg.services.llm_router import chat_completion

        result = await chat_completion([{"role": "user", "content": "test"}])
        assert result == {"content": "just plain text"}

    @patch("odgg.services.llm_router.litellm")
    @patch("odgg.services.llm_router.settings")
    async def test_retries_on_failure(self, mock_settings, mock_litellm):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_model = "gpt-4o"
        mock_settings.llm_api_key = "sk-test"
        mock_settings.llm_base_url = ""
        mock_settings.llm_timeout = 30

        # First call fails, second succeeds
        mock_choice = MagicMock()
        mock_choice.message.content = '{"ok": true}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_litellm.acompletion = AsyncMock(
            side_effect=[Exception("timeout"), mock_response]
        )

        from odgg.services.llm_router import chat_completion

        result = await chat_completion([{"role": "user", "content": "test"}])
        assert result == {"ok": True}
        assert mock_litellm.acompletion.call_count == 2

    @patch("odgg.services.llm_router.litellm")
    @patch("odgg.services.llm_router.settings")
    async def test_raises_after_max_retries(self, mock_settings, mock_litellm):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_model = "gpt-4o"
        mock_settings.llm_api_key = "sk-test"
        mock_settings.llm_base_url = ""
        mock_settings.llm_timeout = 30

        mock_litellm.acompletion = AsyncMock(side_effect=Exception("permanent failure"))

        from odgg.services.llm_router import chat_completion

        with pytest.raises(Exception, match="permanent failure"):
            await chat_completion([{"role": "user", "content": "test"}], max_retries=2)
