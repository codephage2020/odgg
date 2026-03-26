"""LLM router with LiteLLM, two-schema retry strategy, and SSE streaming."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import litellm
from pydantic import BaseModel

from odgg.core.config import settings

logger = logging.getLogger(__name__)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True

# Models that do not support temperature parameter
_NO_TEMPERATURE_MODELS = {"kimi-k2.5"}

# Models that do not support response_format schema (need prompt-based JSON guidance)
_NO_SCHEMA_MODELS = {"kimi-k2.5"}


def _build_model_string() -> str:
    """Build the LiteLLM model string from settings."""
    provider = settings.llm_provider
    model = settings.llm_model

    if provider == "ollama":
        return f"ollama/{model}"
    elif provider == "anthropic":
        return f"anthropic/{model}"
    # OpenAI-compatible providers: prefix with openai/ for LiteLLM routing
    # This works for both native OpenAI and third-party compatible APIs (Kimi, DeepSeek, etc.)
    if model.startswith("openai/"):
        return model
    return f"openai/{model}"


def _get_api_params() -> dict[str, Any]:
    """Build API parameters from settings."""
    params: dict[str, Any] = {}
    if settings.llm_api_key:
        params["api_key"] = settings.llm_api_key
    if settings.llm_base_url:
        params["api_base"] = settings.llm_base_url
    return params


def _model_supports_temperature() -> bool:
    """Check if the current model supports the temperature parameter."""
    return settings.llm_model not in _NO_TEMPERATURE_MODELS


def _model_supports_schema() -> bool:
    """Check if the current model supports response_format with schema."""
    return settings.llm_model not in _NO_SCHEMA_MODELS


async def chat_completion(
    messages: list[dict[str, str]],
    response_model: type[BaseModel] | None = None,
    temperature: float = 0.3,
    max_retries: int = 3,
) -> dict[str, Any] | BaseModel:
    """Send a chat completion request with optional structured output.

    Uses a two-schema strategy:
    - Strict JSON Schema for capable models (GPT-4, Claude)
    - Prompt-based JSON guidance for models without schema support (Kimi, etc.)
    - Relaxed text-parse fallback for Ollama/smaller models
    """
    model = _build_model_string()
    api_params = _get_api_params()

    # For models without schema support, inject JSON instructions into prompt
    if response_model and not _model_supports_schema():
        schema_str = json.dumps(response_model.model_json_schema(), indent=2)
        messages = [
            *messages,
            {
                "role": "user",
                "content": (
                    "You MUST respond with valid JSON only, no markdown or explanation. "
                    f"The JSON must match this schema:\n{schema_str}"
                ),
            },
        ]

    for attempt in range(max_retries):
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "timeout": settings.llm_timeout,
                **api_params,
            }

            # Only set temperature if the model supports it
            if _model_supports_temperature():
                kwargs["temperature"] = temperature

            # Attempt structured output via response_format (only for compatible models)
            if response_model and attempt < 2 and _model_supports_schema():
                schema = response_model.model_json_schema()
                kwargs["response_format"] = {
                    "type": "json_object",
                    "schema": schema,
                }
            elif response_model:
                # For schema-unsupported models, still request json_object mode
                kwargs["response_format"] = {"type": "json_object"}

            response = await litellm.acompletion(**kwargs)
            content = response.choices[0].message.content

            if response_model:
                # Try parsing as the expected model
                try:
                    parsed = json.loads(content)
                    return response_model.model_validate(parsed)
                except (json.JSONDecodeError, Exception) as parse_err:
                    if attempt < max_retries - 1:
                        logger.warning(
                            "Structured output parse failed (attempt %d): %s",
                            attempt + 1,
                            str(parse_err)[:200],
                        )
                        # On retry, reinforce JSON instruction
                        messages = [
                            *messages,
                            {
                                "role": "user",
                                "content": (
                                    "Please respond with valid JSON matching this schema: "
                                    f"{json.dumps(response_model.model_json_schema(), indent=2)}"
                                ),
                            },
                        ]
                        continue
                    raise

            # Return raw dict for unstructured responses
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"content": content}

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning("LLM call failed (attempt %d): %s", attempt + 1, str(e)[:200])
                continue
            raise


async def stream_completion(
    messages: list[dict[str, str]],
    temperature: float = 0.3,
) -> AsyncGenerator[str, None]:
    """Stream a chat completion response as text chunks for SSE."""
    model = _build_model_string()
    api_params = _get_api_params()

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "timeout": settings.llm_timeout,
        "stream": True,
        **api_params,
    }

    # Only set temperature if the model supports it
    if _model_supports_temperature():
        kwargs["temperature"] = temperature

    response = await litellm.acompletion(**kwargs)

    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content
