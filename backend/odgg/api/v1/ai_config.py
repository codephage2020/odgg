"""AI configuration API — view, update, test, and reset LLM settings at runtime."""

from __future__ import annotations

import logging
import time

import litellm
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from odgg.core.config import (
    clear_runtime_overrides,
    get_llm_config,
    get_llm_config_sources,
    update_runtime_overrides,
)
from odgg.core.database import get_db
from odgg.models.ai_config import (
    AiConfigResponse,
    AiConfigRow,
    AiConfigTestRequest,
    AiConfigTestResponse,
    AiConfigUpdate,
    AiPreset,
)
from odgg.services.llm_router import _build_model_string, _get_api_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

_PRESETS: list[AiPreset] = [
    AiPreset(
        label="OpenAI GPT-4o",
        provider="openai",
        model="gpt-4o",
        base_url="",
    ),
    AiPreset(
        label="OpenAI GPT-4o-mini",
        provider="openai",
        model="gpt-4o-mini",
        base_url="",
    ),
    AiPreset(
        label="Anthropic Claude Sonnet",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        base_url="",
    ),
    AiPreset(
        label="DeepSeek V3",
        provider="openai",
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
    ),
    AiPreset(
        label="Ollama (local)",
        provider="ollama",
        model="llama3.1",
        base_url="http://localhost:11434",
    ),
    AiPreset(
        label="Kimi K2.5",
        provider="openai",
        model="kimi-k2.5",
        base_url="https://api.moonshot.cn/v1",
    ),
]


def _mask_api_key(key: str) -> tuple[bool, str]:
    """Return (is_set, hint) for an API key."""
    if not key:
        return False, ""
    if len(key) <= 8:
        return True, key[:2] + "..." + key[-2:]
    return True, key[:3] + "..." + key[-4:]


def _build_response() -> AiConfigResponse:
    """Build the response from effective config."""
    cfg = get_llm_config()
    sources = get_llm_config_sources()
    api_key_set, api_key_hint = _mask_api_key(cfg["api_key"])
    return AiConfigResponse(
        provider=cfg["provider"],
        model=cfg["model"],
        api_key_set=api_key_set,
        api_key_hint=api_key_hint,
        base_url=cfg["base_url"],
        timeout=cfg["timeout"],
        sources=sources,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/ai", response_model=AiConfigResponse)
async def get_ai_config():
    """Return the current effective AI configuration."""
    return _build_response()


@router.put("/ai", response_model=AiConfigResponse)
async def update_ai_config(body: AiConfigUpdate, db: AsyncSession = Depends(get_db)):
    """Update AI configuration. Persists to DB and takes effect immediately."""
    # Upsert singleton row
    row = await db.get(AiConfigRow, 1)
    if not row:
        row = AiConfigRow(id=1)
        db.add(row)

    # Apply non-None fields
    overrides: dict = {}
    if body.provider is not None:
        row.llm_provider = body.provider
        overrides["provider"] = body.provider
    if body.model is not None:
        row.llm_model = body.model
        overrides["model"] = body.model
    if body.api_key is not None:
        row.llm_api_key = body.api_key
        overrides["api_key"] = body.api_key
    if body.base_url is not None:
        row.llm_base_url = body.base_url
        overrides["base_url"] = body.base_url
    if body.timeout is not None:
        row.llm_timeout = body.timeout
        overrides["timeout"] = body.timeout

    await db.commit()
    update_runtime_overrides(overrides)
    logger.info("AI config updated: %s", list(overrides.keys()))
    return _build_response()


@router.delete("/ai", response_model=AiConfigResponse)
async def reset_ai_config(db: AsyncSession = Depends(get_db)):
    """Reset AI configuration to environment variable defaults."""
    row = await db.get(AiConfigRow, 1)
    if row:
        await db.delete(row)
        await db.commit()
    clear_runtime_overrides()
    logger.info("AI config reset to env defaults")
    return _build_response()


@router.post("/ai/test", response_model=AiConfigTestResponse)
async def test_ai_config(body: AiConfigTestRequest):
    """Test an AI connection without persisting settings."""
    # Build a temporary config from current effective + request overrides
    cfg = get_llm_config()
    if body.provider is not None:
        cfg["provider"] = body.provider
    if body.model is not None:
        cfg["model"] = body.model
    if body.api_key is not None:
        cfg["api_key"] = body.api_key
    if body.base_url is not None:
        cfg["base_url"] = body.base_url
    if body.timeout is not None:
        cfg["timeout"] = body.timeout

    model_str = _build_model_string(cfg)
    api_params = _get_api_params(cfg)

    try:
        t0 = time.monotonic()
        response = await litellm.acompletion(
            model=model_str,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            timeout=min(cfg["timeout"], 30),  # cap test timeout
            max_tokens=10,
            **api_params,
        )
        latency = int((time.monotonic() - t0) * 1000)
        content = response.choices[0].message.content.strip()
        return AiConfigTestResponse(
            ok=True,
            message=f"Connected ({model_str}): {content}",
            latency_ms=latency,
        )
    except Exception as e:
        logger.warning("AI config test failed: %s", str(e)[:300])
        return AiConfigTestResponse(
            ok=False,
            message=str(e)[:300],
        )


@router.get("/ai/presets", response_model=list[AiPreset])
async def get_ai_presets():
    """Return available provider presets."""
    return _PRESETS
