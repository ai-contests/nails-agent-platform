"""
Worker 1: Trend Analyst
Input:  List[TrendSignal]
Output: TrendAnalysisResult

Computes composite_score, ranks top-10, detects cross-platform patterns,
flags anomalies with high recent growth.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from nails_agent.models.schemas import TrendSignal, TrendAnalysisResult


_TZ8 = timezone(timedelta(hours=8))


def _composite(sig: TrendSignal) -> float:
    return sig.likes + sig.collects * 1.5 + sig.shares * 2 + sig.comments * 0.5


def _normalise(scores: List[float]) -> List[float]:
    mn, mx = min(scores), max(scores)
    if mx == mn:
        return [50.0] * len(scores)
    return [round((s - mn) / (mx - mn) * 100, 2) for s in scores]


def analyse(signals: List[TrendSignal]) -> TrendAnalysisResult:
    if not signals:
        return TrendAnalysisResult(
            top_10=[], patterns=[], anomalies=[],
            timestamp=datetime.now(_TZ8).isoformat(),
        )

    # 1. Composite scores
    raw_scores = [_composite(s) for s in signals]
    norm = _normalise(raw_scores)
    for sig, score in zip(signals, norm):
        sig.composite_score = score

    # 2. Sort + top-10
    ranked = sorted(signals, key=lambda s: s.composite_score, reverse=True)
    top_10 = ranked[:10]
    for i, sig in enumerate(top_10, 1):
        sig.rank = i

    # 3. Cross-platform pattern detection
    tag_platform: Dict[str, set] = {}
    for sig in signals:
        for tag in sig.style_tags:
            tag_platform.setdefault(tag, set()).add(sig.platform)

    # Pairs of tags that co-occur often across platforms
    pair_counter: Counter = Counter()
    for sig in signals:
        tags = sig.style_tags
        for i in range(len(tags)):
            for j in range(i + 1, len(tags)):
                pair_counter[(tags[i], tags[j])] += 1

    patterns: List[str] = []
    for (t1, t2), cnt in pair_counter.most_common(5):
        platforms_t1 = tag_platform.get(t1, set())
        platforms_t2 = tag_platform.get(t2, set())
        shared = platforms_t1 & platforms_t2
        if len(shared) >= 2 and cnt >= 2:
            patterns.append(
                f"{t1}+{t2} 组合在 {'、'.join(shared)} 跨平台同期出现（共现{cnt}次）"
            )

    if not patterns:
        # Fallback: just list top tags
        top_tags = [t for t, _ in Counter(
            t for s in signals for t in s.style_tags
        ).most_common(3)]
        patterns.append(f"高频风格标签：{'、'.join(top_tags)}")

    # 4. Anomaly detection (captured within 48h, score > mean+1.5*std)
    now = datetime.now(_TZ8)
    scores_arr = [s.composite_score for s in signals]
    mean = sum(scores_arr) / len(scores_arr)
    variance = sum((x - mean) ** 2 for x in scores_arr) / len(scores_arr)
    std = variance ** 0.5

    anomalies: List[str] = []
    for sig in signals:
        try:
            cap = datetime.fromisoformat(sig.captured_at)
            if cap.tzinfo is None:
                cap = cap.replace(tzinfo=_TZ8)
            hours_old = (now - cap).total_seconds() / 3600
        except Exception:
            hours_old = 999

        if hours_old <= 48 and sig.composite_score > mean + 1.5 * std:
            pct = round((sig.composite_score - mean) / mean * 100) if mean else 0
            anomalies.append(
                f"{sig.keyword}（{sig.platform}）近48h热度较均值高{pct}%，疑似爆发信号"
            )
        elif hours_old <= 48 and sig.composite_score >= mean:
            anomalies.append(f"{sig.keyword}（{sig.platform}）为新兴信号")

    return TrendAnalysisResult(
        top_10=top_10,
        patterns=patterns[:5],
        anomalies=anomalies[:5],
        timestamp=datetime.now(_TZ8).isoformat(),
    )


def from_json_file(path: str) -> TrendAnalysisResult:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    signals = [TrendSignal(**item) for item in data]
    return analyse(signals)
