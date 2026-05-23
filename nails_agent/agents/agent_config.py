"""
Shared model client configuration for openai-agents SDK.

Priority: ANTHROPIC_API_KEY → MODELSCOPE_API_KEY → OPENROUTER_API_KEY

The openai-agents SDK is built on the OpenAI client, so Anthropic is reached
via OpenRouter's Claude proxy or a Responses-API-compatible proxy.
ModelScope and OpenRouter both expose OpenAI-compatible endpoints.
"""

from __future__ import annotations

from functools import lru_cache

from nails_agent.services.llm_config import (
    modelscope_config,
    openrouter_config,
    openrouter_referer,
)

_DUMMY_BASE_URL = "http://localhost/v1"


def get_model_string() -> str:
    """Return the model identifier for the active backend."""
    ms = modelscope_config()
    if ms.api_key:
        return ms.model
    router = openrouter_config()
    if router.api_key:
        return router.model
    return ms.model or router.model


@lru_cache(maxsize=1)
def get_openai_client():
    """
    Return a cached AsyncOpenAI client pointed at the available backend.
    Cached so all agents share one HTTP connection pool.
    """
    from agents import AsyncOpenAI

    ms = modelscope_config()
    router = openrouter_config()

    if ms.api_key:
        return AsyncOpenAI(api_key=ms.api_key, base_url=ms.base_url or None)
    if router.api_key:
        headers = {}
        if referer := openrouter_referer():
            headers["HTTP-Referer"] = referer
        return AsyncOpenAI(
            api_key=router.api_key,
            base_url=router.base_url or None,
            default_headers=headers or None,
        )
    # No key — return a dummy client (agents will error gracefully)
    return AsyncOpenAI(api_key="no-key", base_url=_DUMMY_BASE_URL)


def make_model():
    """Return an OpenAIChatCompletionsModel for the active backend."""
    from agents import OpenAIChatCompletionsModel

    return OpenAIChatCompletionsModel(
        model=get_model_string(),
        openai_client=get_openai_client(),
    )


def is_available() -> bool:
    return bool(modelscope_config().api_key or openrouter_config().api_key)
