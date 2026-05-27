"""Centralised LLM environment configuration.

Keep model names, OpenAI-compatible base URLs, and optional routing metadata in
`.env` instead of scattering them across workers and agents.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(Path.home() / ".hermes" / ".env", override=False)


def env_value(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return value.strip()
    return default


@dataclass(frozen=True)
class LLMEndpointConfig:
    model: str = ""
    api_key: str = ""
    base_url: str = ""

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)


def tag_llm_config(
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> LLMEndpointConfig:
    return LLMEndpointConfig(
        model=model or env_value("NAILS_TAG_LLM_MODEL"),
        api_key=api_key or env_value("NAILS_TAG_LLM_API_KEY", "OPENAI_API_KEY"),
        base_url=(base_url or env_value("NAILS_TAG_LLM_BASE_URL", "OPENAI_BASE_URL")).rstrip("/"),
    )


def modelscope_config() -> LLMEndpointConfig:
    return LLMEndpointConfig(
        model=env_value("NAILS_MODELSCOPE_MODEL"),
        api_key=env_value("MODELSCOPE_API_KEY"),
        base_url=env_value("NAILS_MODELSCOPE_BASE_URL", "MODELSCOPE_BASE_URL"),
    )


def openrouter_config() -> LLMEndpointConfig:
    return LLMEndpointConfig(
        model=env_value("NAILS_OPENROUTER_MODEL"),
        api_key=env_value("OPENROUTER_API_KEY"),
        base_url=env_value("NAILS_OPENROUTER_BASE_URL", "OPENROUTER_BASE_URL"),
    )


def anthropic_model() -> str:
    return env_value("NAILS_ANTHROPIC_MODEL", "NAILS_AGENT_MODEL")


def reviewer_model() -> str:
    return env_value("NAILS_REVIEWER_LLM_MODEL", "NAILS_ANTHROPIC_MODEL", "NAILS_AGENT_MODEL")


def hermes_model() -> str:
    return env_value("NAILS_HERMES_MODEL", "NAILS_OPENROUTER_MODEL", "NAILS_AGENT_MODEL")


def openrouter_referer() -> str:
    return env_value("NAILS_OPENROUTER_REFERER")


def vision_tag_config() -> LLMEndpointConfig:
    """Config for vision-based tag extraction.

    Priority:
      1. NAILS_VISION_TAG_API_KEY / NAILS_VISION_TAG_BASE_URL / NAILS_VISION_TAG_MODEL
         (dedicated override — set these if you want a specific VL endpoint)
      2. DashScope with qwen-vl-max  (same key as tag LLM, different model)
      3. OpenRouter with a vision-capable model (qwen/qwen-vl or claude-3-haiku)

    Returns an empty config if no key is found (caller should skip VL enrichment).
    """
    # Explicit override
    dedicated = LLMEndpointConfig(
        model=env_value("NAILS_VISION_TAG_MODEL"),
        api_key=env_value("NAILS_VISION_TAG_API_KEY"),
        base_url=env_value("NAILS_VISION_TAG_BASE_URL").rstrip("/"),
    )
    if dedicated.available:
        return dedicated

    # Reuse DashScope key with qwen-vl-max
    dashscope_key = env_value("NAILS_TAG_LLM_API_KEY", "OPENAI_API_KEY")
    dashscope_url = env_value("NAILS_TAG_LLM_BASE_URL", "OPENAI_BASE_URL").rstrip("/")
    if dashscope_key and dashscope_url:
        return LLMEndpointConfig(
            model=env_value("NAILS_VISION_TAG_MODEL", default="qwen-vl-max"),
            api_key=dashscope_key,
            base_url=dashscope_url,
        )

    # Fallback: OpenRouter (supports vision via many models)
    router_key = env_value("OPENROUTER_API_KEY")
    router_url = env_value(
        "NAILS_OPENROUTER_BASE_URL", "OPENROUTER_BASE_URL",
        default="https://openrouter.ai/api/v1",
    ).rstrip("/")
    if router_key:
        return LLMEndpointConfig(
            model="qwen/qwen2.5-vl-72b-instruct:free",
            api_key=router_key,
            base_url=router_url,
        )

    return LLMEndpointConfig()
