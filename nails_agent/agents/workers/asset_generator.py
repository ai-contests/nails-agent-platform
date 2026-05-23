"""
Worker 2b: Asset Generator
Input:  TrendAnalysisResult
Output: AssetGenerationResult

Generates style card drafts with platform-specific captions + pricing.
Rule-based (no LLM call required for demo).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import List

from nails_agent.models.schemas import (
    TrendAnalysisResult,
    TrendSignal,
    StyleCardDraft,
    PlatformVariant,
    PricingInfo,
    AssetGenerationResult,
)
from nails_agent.services.trend_presentation import sample_label, signal_image_url, tag_summary

_TZ8 = timezone(timedelta(hours=8))

# ── Caption templates ─────────────────────────────────────────────────────────

_XHS_TEMPLATES = [
    "这组{style_desc}绝了！低调有魅力，通勤约会都能驾驭～ ✨",
    "最近爱上这种{style_desc}，质感超绝，看一眼就心动 💅",
    "{style_desc}拍照超出片，美到不像话 🌸",
]
_DOUYIN_TEMPLATES = [
    "{style_desc}✨ 你值得拥有",
    "种草这组{style_desc}，这是今年很值得试的款式",
    "{style_desc}实拍，效果惊艳全场",
]
_IG_TEMPLATES = [
    "Nail look with {tags_en} vibes — effortlessly chic ✨",
    "Obsessed with this nail look! {tags_en} energy only 💅",
    "Spring/Summer must-have nails featuring {tags_en} elements 🌸",
]


def _hashtags(sig: TrendSignal, platform: str) -> List[str]:
    base = ["#美甲"]
    for tag in (sig.style_tags + sig.color_tags + sig.scene_tags)[:4]:
        if tag in {"美甲", "nail"}:
            continue
        base.append(f"#{tag}美甲")
    if platform == "xiaohongshu":
        base += ["#美甲推荐", "#美甲日记"]
    elif platform == "douyin":
        base += ["#美甲教程", "#美甲分享"]
    elif platform == "instagram":
        return ["#nailart", "#nails", "#naildesign", "#nailinspo"]
    return base[:6]


def _pricing(sig: TrendSignal) -> PricingInfo:
    # Price tiers based on material complexity
    if any(t in sig.material_tags for t in ["3D雕花", "硬胶", "镶钻"]):
        return PricingInfo(
            base_price="¥128",
            premium_price="¥268",
            promo_price="¥88",
            premium_reason="高端材料+手工雕花+拍照服务",
        )
    if any(t in sig.material_tags for t in ["猫眼", "磁铁石"]):
        return PricingInfo(
            base_price="¥89",
            premium_price="¥168",
            promo_price="¥59",
            premium_reason="限定磁铁石材料+延长设计+拍照服务",
        )
    return PricingInfo(
        base_price="¥69",
        premium_price="¥128",
        promo_price="¥49",
        premium_reason="精工制作+拍照服务",
    )


def generate(analysis: TrendAnalysisResult) -> AssetGenerationResult:
    drafts: List[StyleCardDraft] = []

    for i, sig in enumerate(analysis.top_10):
        style_name = sample_label(sig, i + 1, with_tags=True)
        style_desc = tag_summary(sig, max_tags=4, empty="趋势美甲")
        tags_en = " & ".join(sig.style_tags[:2]) if sig.style_tags else "aesthetic"

        tmpl_idx = i % len(_XHS_TEMPLATES)
        xhs_caption = _XHS_TEMPLATES[tmpl_idx].format(style_desc=style_desc)
        dy_caption = _DOUYIN_TEMPLATES[tmpl_idx].format(style_desc=style_desc)
        ig_caption = _IG_TEMPLATES[tmpl_idx].format(tags_en=tags_en)

        variants = {
            "xiaohongshu": PlatformVariant(
                caption=xhs_caption,
                hashtags=_hashtags(sig, "xiaohongshu"),
            ),
            "douyin": PlatformVariant(
                caption=dy_caption,
                hashtags=_hashtags(sig, "douyin"),
            ),
            "instagram": PlatformVariant(
                caption=ig_caption,
                hashtags=_hashtags(sig, "instagram"),
            ),
        }

        draft = StyleCardDraft(
            trend_id=sig.trend_id,
            style_name=style_name,
            style_tags=sig.style_tags,
            image_url=signal_image_url(sig),
            platform_variants=variants,
            pricing=_pricing(sig),
        )
        drafts.append(draft)

    return AssetGenerationResult(
        drafts=drafts,
        timestamp=datetime.now(_TZ8).isoformat(),
    )


def from_file(analysis_path: str) -> AssetGenerationResult:
    with open(analysis_path, encoding="utf-8") as f:
        analysis = TrendAnalysisResult(**json.load(f))
    return generate(analysis)
