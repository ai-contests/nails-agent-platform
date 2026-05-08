"""
Worker 4: Summarizer
Input:  PipelineState (all step outputs)
Output: SummaryReport (with .markdown field)
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

from nails_agent.models.schemas import (
    PipelineState,
    SummaryReport,
    ReportSection,
)

_TZ8 = timezone(timedelta(hours=8))


def summarise(state: PipelineState) -> SummaryReport:
    now = datetime.now(_TZ8)
    sections: List[ReportSection] = []

    # ── Section 1: Trend Overview ──────────────────────────────────────────
    trend = state.trend_analysis
    if trend:
        lines = [f"分析周期：{now.strftime('%Y-%m-%d')}  |  来源平台：小红书、抖音、Instagram\n"]
        lines.append(f"**Top 趋势（共 {len(trend.top_10)} 条）**\n")
        for sig in trend.top_10[:5]:
            lines.append(
                f"{sig.rank}. **{sig.keyword}** ({sig.platform})  "
                f"热度 {sig.composite_score:.1f}  标签：{'、'.join(sig.style_tags)}"
            )
        if trend.patterns:
            lines.append("\n**跨平台洞察**")
            for p in trend.patterns:
                lines.append(f"- {p}")
        if trend.anomalies:
            lines.append("\n**异常增速信号**")
            for a in trend.anomalies:
                lines.append(f"- 🚨 {a}")
        sections.append(ReportSection(title="📈 趋势分析", content="\n".join(lines)))

    # ── Section 2: Value Evaluation ────────────────────────────────────────
    value = state.value_evaluation
    if value:
        lines = ["| 排名 | 关键词 | 外部热度 | 增速 | 款式缺口 | 上线优先级 |",
                 "|------|--------|----------|------|----------|------------|"]
        for s in value.snapshots[:5]:
            lines.append(
                f"| {s.rank} | {s.keyword} | {s.external_heat_score:.0f} "
                f"| {s.trend_growth_score:.0f} | {s.style_gap_score:.0f} "
                f"| **{s.launch_priority_score:.0f}** |"
            )
        sections.append(ReportSection(title="💎 价值评估", content="\n".join(lines)))

    # ── Section 3: Campaign Strategy ──────────────────────────────────────
    campaign = state.campaign_strategy
    if campaign:
        lines = []
        p0 = [c for c in campaign.style_cards if c.schedule and c.schedule.priority == "P0"]
        p1 = [c for c in campaign.style_cards if c.schedule and c.schedule.priority == "P1"]
        p2 = [c for c in campaign.style_cards if c.schedule and c.schedule.priority == "P2"]
        if p0:
            lines.append(f"**P0 立即上线（{len(p0)} 款）**")
            for c in p0:
                lines.append(f"- {c.style_name}  |  定价 {c.pricing.base_price if c.pricing else 'N/A'}  |  小红书发布 {c.schedule.xiaohongshu_publish_at[:10] if c.schedule else 'TBD'}")
        if p1:
            lines.append(f"\n**P1 本周上线（{len(p1)} 款）**")
            for c in p1[:3]:
                lines.append(f"- {c.style_name}  |  定价 {c.pricing.base_price if c.pricing else 'N/A'}")
        if p2:
            lines.append(f"\n**P2 下周排期（{len(p2)} 款）**")
            for c in p2[:2]:
                lines.append(f"- {c.style_name}")
        sections.append(ReportSection(title="📣 运营策略", content="\n".join(lines)))

    # ── Section 4: Assets Summary ──────────────────────────────────────────
    assets = state.asset_generation
    if assets:
        total = len(assets.drafts)
        platforms = {"小红书", "抖音", "Instagram"}
        lines = [
            f"共生成 **{total} 张**款式运营卡片，覆盖 {len(platforms)} 个平台。",
            "",
            "**样例文案（小红书）**",
        ]
        for draft in assets.drafts[:2]:
            xhs = draft.platform_variants.get("xiaohongshu")
            if xhs:
                lines.append(f"> {xhs.caption}")
                lines.append(f"> {' '.join(xhs.hashtags[:4])}")
                lines.append("")
        sections.append(ReportSection(title="🎨 素材资产", content="\n".join(lines)))

    # ── Build markdown ─────────────────────────────────────────────────────
    md_parts = [
        "# 美甲 AI 运营平台 — 智能运营报告",
        f"> 生成时间：{now.strftime('%Y-%m-%d %H:%M')}  |  Pipeline ID: `{state.pipeline_id}`",
        "",
    ]
    for sec in sections:
        md_parts.append(f"## {sec.title}")
        md_parts.append(sec.content)
        md_parts.append("")

    # ── Top-3 keywords ─────────────────────────────────────────────────────
    top_3: List[str] = []
    if value and value.snapshots:
        top_3 = [s.keyword for s in value.snapshots[:3]]
    elif trend and trend.top_10:
        top_3 = [s.keyword for s in trend.top_10[:3]]

    return SummaryReport(
        pipeline_id=state.pipeline_id,
        sections=sections,
        top_3_keywords=top_3,
        total_trends_analyzed=len(trend.top_10) if trend else 0,
        total_style_cards=len(campaign.style_cards) if campaign else 0,
        markdown="\n".join(md_parts),
        timestamp=now.isoformat(),
    )
