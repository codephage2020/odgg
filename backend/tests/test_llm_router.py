"""Tests for LLM router — model string building and API params."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from odgg.services.llm_router import _build_model_string, _get_api_params


def _mock_cfg(**overrides):
    """Build a mock LLM config dict with defaults."""
    cfg = {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "",
        "base_url": "",
        "timeout": 30,
    }
    cfg.update(overrides)
    return cfg


class TestBuildModelString:
    def test_openai_provider(self):
        cfg = _mock_cfg(provider="openai", model="gpt-4o")
        assert _build_model_string(cfg) == "openai/gpt-4o"

    def test_ollama_provider(self):
        cfg = _mock_cfg(provider="ollama", model="llama3.1")
        assert _build_model_string(cfg) == "ollama/llama3.1"

    def test_anthropic_provider(self):
        cfg = _mock_cfg(provider="anthropic", model="claude-3-sonnet")
        assert _build_model_string(cfg) == "anthropic/claude-3-sonnet"


class TestGetApiParams:
    def test_with_api_key(self):
        cfg = _mock_cfg(api_key="sk-test123", base_url="")
        params = _get_api_params(cfg)
        assert params["api_key"] == "sk-test123"
        assert "api_base" not in params

    def test_with_base_url(self):
        cfg = _mock_cfg(api_key="", base_url="http://localhost:11434")
        params = _get_api_params(cfg)
        assert params["api_base"] == "http://localhost:11434"
        assert "api_key" not in params

    def test_both_params(self):
        cfg = _mock_cfg(api_key="sk-key", base_url="http://localhost:11434")
        params = _get_api_params(cfg)
        assert "api_key" in params
        assert "api_base" in params

    def test_no_params(self):
        cfg = _mock_cfg(api_key="", base_url="")
        params = _get_api_params(cfg)
        assert params == {}


class TestChatCompletion:
    @patch("odgg.services.llm_router.litellm")
    @patch("odgg.services.llm_router.get_llm_config")
    async def test_returns_parsed_json(self, mock_get_cfg, mock_litellm):
        mock_get_cfg.return_value = _mock_cfg(api_key="sk-test")

        mock_choice = MagicMock()
        mock_choice.message.content = '{"result": "test"}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        from odgg.services.llm_router import chat_completion

        result = await chat_completion([{"role": "user", "content": "test"}])
        assert result == {"result": "test"}

    @patch("odgg.services.llm_router.litellm")
    @patch("odgg.services.llm_router.get_llm_config")
    async def test_non_json_returns_content(self, mock_get_cfg, mock_litellm):
        mock_get_cfg.return_value = _mock_cfg(api_key="sk-test")

        mock_choice = MagicMock()
        mock_choice.message.content = "just plain text"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        from odgg.services.llm_router import chat_completion

        result = await chat_completion([{"role": "user", "content": "test"}])
        assert result == {"content": "just plain text"}

    @patch("odgg.services.llm_router.litellm")
    @patch("odgg.services.llm_router.get_llm_config")
    async def test_retries_on_failure(self, mock_get_cfg, mock_litellm):
        mock_get_cfg.return_value = _mock_cfg(api_key="sk-test")

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
    @patch("odgg.services.llm_router.get_llm_config")
    async def test_raises_after_max_retries(self, mock_get_cfg, mock_litellm):
        mock_get_cfg.return_value = _mock_cfg(api_key="sk-test")

        mock_litellm.acompletion = AsyncMock(side_effect=Exception("permanent failure"))

        from odgg.services.llm_router import chat_completion

        with pytest.raises(Exception, match="permanent failure"):
            await chat_completion([{"role": "user", "content": "test"}], max_retries=2)
