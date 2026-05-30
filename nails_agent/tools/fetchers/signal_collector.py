"""
SignalCollector — unified entry point for trend signal collection.

Active sources (all FREE):
  1. XHS CDP      — real Chrome via CDP (primary; requires --remote-debugging-port=9222)
  2. XHS-MCP      — local Go xiaohongshu-mcp server (port 18060, REST API; fallback)
  3. Douyin CDP   — reuses logged-in Chrome tab  (requires --remote-debugging-port=9222)
  4. Instagram    — playwright CDP or instaloader session
  5. Mock         — web/data/trend_signals.json  (always available as fallback)

Disabled / suspended sources:
  - XHSSkillsFetcher — Node.js xhs-mcp wrapper; replaced by Go xhs-mcp
  - TikHub           — paid API; enable by setting TIKHUB_API_KEY

Usage:
    collector = SignalCollector()
    print(collector.source_status())
    signals = collector.collect()
"""

from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

from nails_agent.models.schemas import RejectedTrendCandidate, TrendSignal

logger = logging.getLogger(__name__)

# Per-platform keyword sets (5 each) — targets ≥100 signals/platform/round.

# Chinese terms work best on XHS (cover scene + intent + style).
# XHS now search-enriches only the highest-engagement candidates with detail calls,
# so keep the per-keyword search page shallow to reduce runtime and account risk.
# ── XHS keyword pool ──────────────────────────────────────────────────────────
# Organised by dimension so each search run samples across different axes.
# Each category contributes different signals — avoids top-10 converging on
# the same posts.

XHS_KEYWORD_POOL: dict[str, list[str]] = {
    # 色系 — colour-family searches surface colour trends first
    "色系": [
        "猫眼美甲",
        "渐变色美甲",
        "法式美甲",
        "奶油色美甲",
        "多巴胺美甲",
        "纯色美甲",
        "莫兰迪美甲",
    ],
    # 场景 — context/occasion-driven posts skew toward real-use nail photos
    "场景": ["夏日美甲", "约会美甲", "日常美甲", "通勤美甲", "婚礼美甲", "秋冬美甲"],
    # 风格 — aesthetic style keywords
    "风格": [
        "简约美甲",
        "ins风美甲",
        "复古美甲",
        "甜酷美甲",
        "高级感美甲",
        "韩系美甲",
        "冷淡风美甲",
    ],
    # 甲型 — nail shape/length
    "甲型": ["长甲美甲设计", "短甲美甲", "方形甲", "圆形甲", "杏仁甲"],
    # 工艺 — technique/material
    "工艺": ["猫眼甲", "亮片美甲", "光疗甲推荐", "镭射美甲", "晕染美甲", "贴片美甲"],
    # 合集 — compilation posts (multi-image, higher chance of 9-grid covers)
    "合集": ["美甲款式合集", "春季美甲合集", "美甲灵感合集", "2025美甲流行"],
}

# Default 9-keyword set sampled across all dimensions (one per bucket).
# Rotated each run via collect_signals; override via keywords= param.
XHS_KEYWORDS = [
    "猫眼美甲",  # 色系
    "夏日美甲",  # 场景
    "简约美甲",  # 风格
    "短甲美甲",  # 甲型
    "光疗甲推荐",  # 工艺
    "法式美甲",  # 色系 — second colour pick
    "约会美甲",  # 场景 — second scene pick
    "美甲款式合集",  # 合集 — multi-image posts
    "韩系美甲",  # 风格 — second style pick
]


def sample_xhs_keywords(n: int = 7, *, seed: int | None = None) -> list[str]:
    """Return *n* XHS keywords sampled one-per-dimension, then filling with
    remaining pool entries.  Pass *seed* for reproducible results in tests."""
    import random as _random

    rng = _random.Random(seed)
    chosen: list[str] = []
    buckets = list(XHS_KEYWORD_POOL.values())
    # One from each bucket first
    for bucket in buckets:
        chosen.append(rng.choice(bucket))
        if len(chosen) >= n:
            return chosen
    # Fill remaining slots from pool (excluding already chosen)
    remaining = [kw for kws in buckets for kw in kws if kw not in chosen]
    rng.shuffle(remaining)
    for kw in remaining:
        if len(chosen) >= n:
            break
        chosen.append(kw)
    return chosen[:n]


# Douyin: lean toward tutorial/showcase content
DOUYIN_KEYWORDS = [
    "美甲教程",
    "猫眼美甲",
    "法式美甲",
    "夏日美甲",
    "高级感美甲",
]

# Instagram hashtags (no #) — mix style + general nail tags
IG_NAIL_TAGS = [
    "nailart",
    "cateyenails",
    "frenchnails",
    "gradientnails",
    "3dnailart",
]

# Used by clients (orchestrator, etc.) that want a generic keyword set
DEFAULT_NAIL_KEYWORDS = XHS_KEYWORDS

# Per-platform per-keyword target. XHS detail enrichment then keeps global Top 10.
# 20 per keyword × 9 keywords = ~180 candidates before dedup → gives detail pool of 20
# → stable Top 10 output even when a few detail calls fail with "Note not found".
_PER_KW_LIMIT = 20


class SignalCollector:
    """
    Aggregates trend signals from multiple FREE data sources with graceful fallback.
    All fetchers are lazy-loaded and fail-safe.
    """

    def __init__(
        self,
        mock_data_path: Optional[str] = None,
        cdp_url: str = "http://localhost:9222",
        xhs_skills_dir: Optional[Path] = None,
        ig_session_file: Optional[str] = None,
        xhs_mcp_url: str = "http://localhost:18060",
        # Optional paid source
        tikhub_api_key: Optional[str] = None,
    ):
        self._mock_path = mock_data_path
        self._cdp_url = cdp_url
        self._xhs_dir = xhs_skills_dir
        self._ig_session = ig_session_file
        self._xhs_mcp_url = xhs_mcp_url
        self._tikhub_key = tikhub_api_key or os.environ.get("TIKHUB_API_KEY", "")

        # Lazy instances
        self._xhs_mcp = None
        self._xhs_cdp = None
        self._douyin = None
        self._instagram = None
        self._tikhub = None
        self.rejected_candidates: List[RejectedTrendCandidate] = []
        self.last_collection_used_mock = False
        self.last_collection_sources: List[str] = []
        self.last_collection_real_sources_attempted = False

    # ── Lazy fetcher getters ──────────────────────────────────────────────────

    def _get_xhs_mcp(self):
        if self._xhs_mcp is None:
            from nails_agent.tools.fetchers.xhs_mcp_fetcher import XHSMCPFetcher

            self._xhs_mcp = XHSMCPFetcher(base_url=self._xhs_mcp_url)
        return self._xhs_mcp

    def _get_xhs_cdp(self):
        if self._xhs_cdp is None:
            from nails_agent.tools.fetchers.xhs_cdp_fetcher import XHSCDPFetcher

            self._xhs_cdp = XHSCDPFetcher(cdp_url=self._cdp_url)
        return self._xhs_cdp

    def _get_douyin(self):
        if self._douyin is None:
            from nails_agent.tools.fetchers.douyin_cdp import DouyinCDPFetcher

            self._douyin = DouyinCDPFetcher(cdp_url=self._cdp_url)
        return self._douyin

    def _get_instagram(self):
        if self._instagram is None:
            from nails_agent.tools.fetchers.instagram_fetcher import InstagramFetcher

            self._instagram = InstagramFetcher(session_file=self._ig_session)
        return self._instagram

    def _get_tikhub(self):
        if self._tikhub is None:
            from nails_agent.tools.fetchers.tikhub_fetcher import TikHubFetcher

            self._tikhub = TikHubFetcher(api_key=self._tikhub_key)
        return self._tikhub

    # ── Status ────────────────────────────────────────────────────────────────

    def source_status(self, refresh: bool = False) -> Dict[str, bool]:
        """Non-blocking check of which sources are ready."""
        status: Dict[str, bool] = {}
        try:
            status["xhs_cdp"] = self._get_xhs_cdp().is_available()
        except Exception:
            status["xhs_cdp"] = False
        try:
            status["xhs"] = self._get_xhs_mcp().is_available(force_refresh=refresh)
        except Exception:
            status["xhs"] = False
        try:
            status["douyin_cdp"] = self._get_douyin().is_available()
        except Exception:
            status["douyin_cdp"] = False
        try:
            status["instagram"] = self._get_instagram().is_available()
        except Exception:
            status["instagram"] = False
        status["tikhub"] = bool(self._tikhub_key)
        status["mock"] = self._mock_data_available()
        return status

    # ── Collection ────────────────────────────────────────────────────────────

    def collect(
        self,
        keywords: Optional[List[str]] = None,
        limit_per_kw: int = _PER_KW_LIMIT,
        since_days: Optional[int] = None,
        use_xhs: bool = True,
        use_douyin: bool = True,
        use_instagram: bool = True,
        use_tikhub: bool = True,
        use_mock_fallback: bool = True,
        refresh_sources: bool = True,
        download_xhs_images: bool = True,
        xhs_image_dir: str = "web/output/images/latest/raw",
        xhs_max_images_per_signal: int = 3,
        xhs_detail_candidate_n: int = 20,
        xhs_detail_retry_attempts: int = 2,
        xhs_use_llm_tags: bool = True,
        parallel: bool = True,
    ) -> List[TrendSignal]:
        """
        Collect from all available sources (parallel by default).

        Each platform uses its own 5-keyword set targeting ~100 signals per
        platform per round. Pass `keywords` to override the union (used by
        XHS + Douyin; IG uses english hashtags regardless).

        Args:
            since_days: If set, drop signals whose publish_time is older
                than N days. Signals with empty/unknown publish_time
                (e.g. XHS search feeds) are kept regardless — they're
                marked unknown, not aged-out.
            download_xhs_images: If True, download enriched XHS cover images
                to `xhs_image_dir` and put paths on TrendSignal.local_image_paths.
            xhs_max_images_per_signal: Local download cap per TrendSignal. Remote
                image_urls still keeps every URL returned by detail.
            xhs_detail_candidate_n: Search candidates considered for detail
                enrichment after interaction-score ranking.
            xhs_detail_retry_attempts: Detail request attempts per candidate.

        Returns deduplicated List[TrendSignal] sorted by engagement score.
        Falls back to mock data only if all real sources produce nothing.
        """
        # Sample diverse keywords every run so top-10 results span different
        # colour / scene / style / technique dimensions.
        xhs_kws = keywords or sample_xhs_keywords(n=len(XHS_KEYWORDS))
        douyin_kws = keywords or DOUYIN_KEYWORDS
        ig_tags = IG_NAIL_TAGS  # english hashtags — not parametrised

        all_signals: List[TrendSignal] = []
        sources_used: List[str] = []
        tasks: Dict[str, callable] = {}
        self.rejected_candidates = []
        self.last_collection_used_mock = False
        self.last_collection_sources = []
        self.last_collection_real_sources_attempted = False

        if use_xhs:
            # Prefer real Chrome via CDP (avoids Playwright bot-detection rate-limits).
            # Falls back to XHS-MCP (Go bridge + Playwright) when CDP is unavailable.
            xhs_cdp = self._get_xhs_cdp()
            xhs_mcp = self._get_xhs_mcp()
            cdp_ready = False
            try:
                cdp_ready = xhs_cdp.is_available()
            except Exception:
                pass

            if cdp_ready:

                def _run_xhs_cdp():
                    return xhs_cdp.search_many(xhs_kws, target_per_kw=limit_per_kw)

                tasks["xhs"] = _run_xhs_cdp
                logger.info("XHS: using CDP fetcher (real Chrome, no bot-detection)")
            elif xhs_mcp.is_available(force_refresh=refresh_sources):

                def _run_xhs():
                    results = xhs_mcp.search(
                        xhs_kws,
                        limit_per_kw=limit_per_kw,
                        detail_top_n=10,
                        detail_candidate_n=xhs_detail_candidate_n,
                        detail_retry_attempts=xhs_detail_retry_attempts,
                        enrich_detail=True,
                        use_llm_tags=xhs_use_llm_tags,
                        download_images=download_xhs_images,
                        image_dir=xhs_image_dir,
                        max_images_per_signal=xhs_max_images_per_signal,
                    )
                    self.rejected_candidates.extend(xhs_mcp.rejected_candidates)
                    return results

                tasks["xhs"] = _run_xhs
                logger.info("XHS: using MCP fetcher (Playwright bridge)")
            else:
                logger.debug("XHS: neither CDP nor MCP available")

        if use_douyin:
            dy = self._get_douyin()
            if dy.is_available():
                tasks["douyin"] = lambda: dy.search(douyin_kws, limit_per_kw=limit_per_kw)
            else:
                logger.debug("Douyin CDP: Chrome not running with debug port")

        if use_instagram:
            ig = self._get_instagram()
            if ig.is_available():
                tasks["instagram"] = lambda: ig.fetch_all(ig_tags, limit_per_tag=limit_per_kw)
            else:
                logger.debug("Instagram: neither CDP nor instaloader available")

        if use_tikhub and self._tikhub_key:
            tasks["tikhub"] = lambda: self._get_tikhub().fetch_all(
                xhs_kws, limit_per_kw=limit_per_kw
            )

        real_sources_attempted = bool(tasks)
        self.last_collection_real_sources_attempted = real_sources_attempted

        # Execute tasks
        # 5 keywords × scroll/source is slow: XHS ~50s, Douyin ~120s, IG ~150s.
        # Cap at 4 min per source to bound total runtime when one platform stalls.
        if parallel and len(tasks) > 1:
            with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as pool:
                futures = {pool.submit(fn): name for name, fn in tasks.items()}
                for fut in as_completed(futures):
                    name = futures[fut]
                    try:
                        results = fut.result(timeout=240)
                        if results:
                            all_signals.extend(results)
                            sources_used.append(f"{name}({len(results)})")
                            logger.info("Source %s: %d signals", name, len(results))
                    except Exception as e:
                        logger.error("Source %s failed: %s", name, e)
        else:
            for name, fn in tasks.items():
                try:
                    results = fn()
                    if results:
                        all_signals.extend(results)
                        sources_used.append(f"{name}({len(results)})")
                except Exception as e:
                    logger.error("Source %s failed: %s", name, e)

        # Fallback to mock only when no real source was available. If a real
        # source was attempted but returned no detail-enriched signals, surface
        # that result instead of masking it with mock data.
        if not all_signals and use_mock_fallback and not real_sources_attempted:
            mock = self._load_mock()
            if mock:
                all_signals = mock
                sources_used.append(f"mock({len(mock)})")
                self.last_collection_used_mock = True
                logger.info("Fallback to mock: %d signals", len(mock))
        elif not all_signals and real_sources_attempted:
            logger.warning("Real sources were attempted but returned no usable signals")

        # Optional recency filter (publish_time known and within window)
        if since_days is not None and all_signals:
            before = len(all_signals)
            all_signals = self._filter_by_age(all_signals, since_days)
            dropped = before - len(all_signals)
            if dropped:
                logger.info(
                    "Recency filter (≤%dd): dropped %d/%d signals", since_days, dropped, before
                )

        if sources_used:
            logger.info("Sources: %s → %d total", ", ".join(sources_used), len(all_signals))
        else:
            logger.warning("No data sources available — returning empty")

        self.last_collection_sources = sources_used
        return self._dedup_and_sort(all_signals)

    @staticmethod
    def _filter_by_age(signals: List[TrendSignal], days: int) -> List[TrendSignal]:
        """Drop signals older than `days`. Empty publish_time → kept (unknown ≠ old)."""
        from datetime import datetime, timezone, timedelta

        tz8 = timezone(timedelta(hours=8))
        cutoff = datetime.now(tz8) - timedelta(days=days)
        kept = []
        for s in signals:
            if not s.publish_time:
                kept.append(s)  # unknown date → keep
                continue
            try:
                pub = datetime.fromisoformat(s.publish_time)
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=tz8)
                if pub >= cutoff:
                    kept.append(s)
            except Exception:
                kept.append(s)  # un-parseable → keep (don't silently drop)
        return kept

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _mock_data_available(self) -> bool:
        p = self._resolve_mock_path()
        return p is not None and p.exists()

    def _resolve_mock_path(self) -> Optional[Path]:
        if self._mock_path:
            p = Path(self._mock_path)
            return p if p.exists() else None
        for p in [
            Path("web/data/trend_signals.json"),
            Path("web/data/trend_signals_with_score.json"),
        ]:
            if p.exists():
                return p
        return None

    def _load_mock(self) -> List[TrendSignal]:
        path = self._resolve_mock_path()
        if not path:
            return []
        try:
            with open(path, encoding="utf-8") as f:
                return [TrendSignal(**item) for item in json.load(f)]
        except Exception as e:
            logger.error("Mock data load error: %s", e)
            return []

    def _dedup_and_sort(self, signals: List[TrendSignal]) -> List[TrendSignal]:
        seen: set = set()
        deduped = []
        for s in signals:
            if s.trend_id not in seen:
                seen.add(s.trend_id)
                deduped.append(s)
        deduped.sort(
            key=lambda s: s.likes + s.collects * 1.5 + s.shares * 2 + s.comments * 0.5,
            reverse=True,
        )
        return deduped
