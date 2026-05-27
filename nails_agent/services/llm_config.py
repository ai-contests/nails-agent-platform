"""Centralised LLM environment configuration.

Provider priority (first available wins):
  1. ModelScope  — MODELSCOPE_API_KEY  (https://api-inference.modelscope.cn/v1)
  2. DashScope   — NAILS_TAG_LLM_API_KEY / OPENAI_API_KEY
  3. OpenRouter  — OPENROUTER_API_KEY

Both ModelScope and DashScope expose OpenAI-compatible `/v1/chat/completions`.
ModelScope vision models: Qwen/Qwen2.5-VL-72B-Instruct
DashScope vision models:  qwen-vl-max
OpenRouter vision models: qwen/qwen2.5-vl-72b-instruct:free
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


# ── Per-provider helpers ───────────────────────────────────────────────────────

def modelscope_config() -> LLMEndpointConfig:
    """ModelScope API-Inference (OpenAI-compatible, bearer auth)."""
    return LLMEndpointConfig(
        model=env_value("NAILS_MODELSCOPE_MODEL", default="Qwen/Qwen3-235B-A22B-Instruct-2507"),
        api_key=env_value("MODELSCOPE_API_KEY"),
        base_url=env_value(
            "NAILS_MODELSCOPE_BASE_URL", "MODELSCOPE_BASE_URL",
            default="https://api-inference.modelscope.cn/v1",
        ).rstrip("/"),
    )


def dashscope_config() -> LLMEndpointConfig:
    """DashScope (Alibaba Cloud) OpenAI-compatible endpoint."""
    return LLMEndpointConfig(
        model=env_value("NAILS_TAG_LLM_MODEL", default="qwen3-max"),
        api_key=env_value("NAILS_TAG_LLM_API_KEY", "OPENAI_API_KEY"),
        base_url=env_value(
            "NAILS_TAG_LLM_BASE_URL", "OPENAI_BASE_URL",
            default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ).rstrip("/"),
    )


def openrouter_config() -> LLMEndpointConfig:
    """OpenRouter (multi-provider proxy, OpenAI-compatible)."""
    return LLMEndpointConfig(
        model=env_value(
            "NAILS_OPENROUTER_MODEL",
            default="anthropic/claude-sonnet-4-5",
        ),
        api_key=env_value("OPENROUTER_API_KEY"),
        base_url=env_value(
            "NAILS_OPENROUTER_BASE_URL", "OPENROUTER_BASE_URL",
            default="https://openrouter.ai/api/v1",
        ).rstrip("/"),
    )


# ── Composite config selectors ─────────────────────────────────────────────────

def tag_llm_config(
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> LLMEndpointConfig:
    """Text-only LLM for tag extraction.

    Explicit params > NAILS_TAG_LLM_* env vars > ModelScope > DashScope > OpenRouter.
    """
    # Explicit caller override
    if model or api_key or base_url:
        return LLMEndpointConfig(
            model=model or env_value("NAILS_TAG_LLM_MODEL"),
            api_key=api_key or env_value("NAILS_TAG_LLM_API_KEY", "OPENAI_API_KEY"),
            base_url=(base_url or env_value("NAILS_TAG_LLM_BASE_URL", "OPENAI_BASE_URL")).rstrip("/"),
        )

    # Env-configured dedicated tag endpoint (covers both ModelScope and DashScope
    # when NAILS_TAG_LLM_* vars are set — as done in .env)
    dedicated = LLMEndpointConfig(
        model=env_value("NAILS_TAG_LLM_MODEL"),
        api_key=env_value("NAILS_TAG_LLM_API_KEY"),
        base_url=env_value("NAILS_TAG_LLM_BASE_URL").rstrip("/"),
    )
    if dedicated.available:
        return dedicated

    # Provider auto-detect: ModelScope → DashScope → OpenRouter
    for cfg in (modelscope_config(), dashscope_config(), openrouter_config()):
        if cfg.available:
            return cfg

    return LLMEndpointConfig()


def vision_tag_config() -> LLMEndpointConfig:
    """Vision LLM for image-based tag extraction.

    Priority:
      1. NAILS_VISION_TAG_* env vars (explicit override)
      2. ModelScope  — Qwen/Qwen2.5-VL-72B-Instruct
      3. DashScope   — qwen-vl-max  (same key as tag LLM)
      4. OpenRouter  — qwen/qwen2.5-vl-72b-instruct:free
    """
    # Explicit dedicated override
    dedicated = LLMEndpointConfig(
        model=env_value("NAILS_VISION_TAG_MODEL"),
        api_key=env_value("NAILS_VISION_TAG_API_KEY"),
        base_url=env_value("NAILS_VISION_TAG_BASE_URL").rstrip("/"),
    )
    if dedicated.available:
        return dedicated

    # ModelScope vision
    ms = modelscope_config()
    if ms.api_key:
        return LLMEndpointConfig(
            model="Qwen/Qwen2.5-VL-72B-Instruct",
            api_key=ms.api_key,
            base_url=ms.base_url or "https://api-inference.modelscope.cn/v1",
        )

    # DashScope vision
    ds = dashscope_config()
    if ds.api_key:
        return LLMEndpointConfig(
            model="qwen-vl-max",
            api_key=ds.api_key,
            base_url=ds.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    # OpenRouter vision (free tier)
    router_key = env_value("OPENROUTER_API_KEY")
    if router_key:
        return LLMEndpointConfig(
            model="qwen/qwen2.5-vl-72b-instruct:free",
            api_key=router_key,
            base_url=env_value(
                "NAILS_OPENROUTER_BASE_URL", "OPENROUTER_BASE_URL",
                default="https://openrouter.ai/api/v1",
            ).rstrip("/"),
        )

    return LLMEndpointConfig()


def anthropic_model() -> str:
    return env_value("NAILS_ANTHROPIC_MODEL", "NAILS_AGENT_MODEL")


def reviewer_model() -> str:
    return env_value("NAILS_REVIEWER_LLM_MODEL", "NAILS_ANTHROPIC_MODEL", "NAILS_AGENT_MODEL")


def hermes_model() -> str:
    return env_value("NAILS_HERMES_MODEL", "NAILS_OPENROUTER_MODEL", "NAILS_AGENT_MODEL")


def openrouter_referer() -> str:
    return env_value("NAILS_OPENROUTER_REFERER")
