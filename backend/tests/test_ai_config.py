"""Tests for AI configuration API and runtime config resolution."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from odgg.app import app
from odgg.core.config import (
    clear_runtime_overrides,
    get_llm_config,
    get_llm_config_sources,
    settings,
    update_runtime_overrides,
)


@pytest.fixture(autouse=True)
def _clean_overrides():
    """Ensure runtime overrides are clean before/after each test."""
    clear_runtime_overrides()
    yield
    clear_runtime_overrides()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Unit tests: config resolution layer
# ---------------------------------------------------------------------------


class TestConfigResolution:
    def test_defaults_from_env(self):
        cfg = get_llm_config()
        assert cfg["provider"] == settings.llm_provider
        assert cfg["model"] == settings.llm_model
        assert cfg["timeout"] == settings.llm_timeout

    def test_override_partial(self):
        update_runtime_overrides({"model": "gpt-4o-mini"})
        cfg = get_llm_config()
        assert cfg["model"] == "gpt-4o-mini"
        # Other fields still from env
        assert cfg["provider"] == settings.llm_provider

    def test_override_full(self):
        update_runtime_overrides({
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key": "sk-test-123",
            "base_url": "https://api.example.com",
            "timeout": 60,
        })
        cfg = get_llm_config()
        assert cfg["provider"] == "anthropic"
        assert cfg["model"] == "claude-sonnet-4-20250514"
        assert cfg["api_key"] == "sk-test-123"
        assert cfg["base_url"] == "https://api.example.com"
        assert cfg["timeout"] == 60

    def test_clear_overrides(self):
        update_runtime_overrides({"model": "custom-model"})
        clear_runtime_overrides()
        cfg = get_llm_config()
        assert cfg["model"] == settings.llm_model

    def test_sources_all_env(self):
        sources = get_llm_config_sources()
        assert all(v == "env" for v in sources.values())

    def test_sources_mixed(self):
        update_runtime_overrides({"model": "custom"})
        sources = get_llm_config_sources()
        assert sources["model"] == "user"
        assert sources["provider"] == "env"

    def test_none_values_ignored(self):
        update_runtime_overrides({"model": None, "provider": "ollama"})
        cfg = get_llm_config()
        assert cfg["provider"] == "ollama"
        assert cfg["model"] == settings.llm_model


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestAiConfigApi:
    async def test_get_returns_defaults(self, client: AsyncClient):
        resp = await client.get("/api/v1/config/ai")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == settings.llm_provider
        assert data["model"] == settings.llm_model
        assert "sources" in data

    async def test_get_api_key_masked(self, client: AsyncClient):
        # Set a key via runtime override so we can test masking
        update_runtime_overrides({"api_key": "sk-test-1234567890abcdef"})
        resp = await client.get("/api/v1/config/ai")
        data = resp.json()
        assert data["api_key_set"] is True
        assert "..." in data["api_key_hint"]
        assert "1234567890" not in data["api_key_hint"]  # key not fully exposed

    async def test_put_updates_config(self, client: AsyncClient):
        resp = await client.put(
            "/api/v1/config/ai",
            json={"provider": "anthropic", "model": "claude-sonnet-4-20250514", "timeout": 60},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-sonnet-4-20250514"
        assert data["timeout"] == 60
        assert data["sources"]["provider"] == "user"
        assert data["sources"]["model"] == "user"

    async def test_put_partial_preserves_other_fields(self, client: AsyncClient):
        # First set provider
        await client.put("/api/v1/config/ai", json={"provider": "ollama"})
        # Then update only model
        resp = await client.put("/api/v1/config/ai", json={"model": "llama3.1"})
        data = resp.json()
        assert data["provider"] == "ollama"
        assert data["model"] == "llama3.1"

    async def test_get_after_put_reflects_changes(self, client: AsyncClient):
        await client.put("/api/v1/config/ai", json={"model": "gpt-4o-mini"})
        resp = await client.get("/api/v1/config/ai")
        assert resp.json()["model"] == "gpt-4o-mini"

    async def test_delete_resets_to_defaults(self, client: AsyncClient):
        await client.put("/api/v1/config/ai", json={"model": "custom"})
        resp = await client.delete("/api/v1/config/ai")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == settings.llm_model
        assert all(v == "env" for v in data["sources"].values())

    async def test_put_api_key_masked_in_response(self, client: AsyncClient):
        resp = await client.put(
            "/api/v1/config/ai", json={"api_key": "sk-secret-key-12345678"}
        )
        data = resp.json()
        assert data["api_key_set"] is True
        assert "secret" not in data["api_key_hint"]

    async def test_presets_not_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/config/ai/presets")
        assert resp.status_code == 200
        presets = resp.json()
        assert len(presets) > 0
        assert all("label" in p for p in presets)
        assert all("provider" in p for p in presets)
        assert all("model" in p for p in presets)


class TestAiConfigTestEndpoint:
    async def test_invalid_key_returns_error(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/config/ai/test",
            json={"provider": "openai", "model": "gpt-4o", "api_key": "sk-invalid"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert len(data["message"]) > 0
