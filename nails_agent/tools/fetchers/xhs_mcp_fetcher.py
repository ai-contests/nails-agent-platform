"""
XHS-MCP fetcher — talks to the Go xiaohongshu-mcp HTTP server.

The Go server (xpzouying/xiaohongshu-mcp) exposes REST endpoints in
addition to the MCP protocol. We hit `/api/v1/feeds/search` and
`/api/v1/feeds/list` directly — simpler than MCP handshake, same data.

Server must be running:
    cd /tmp/xiaohongshu-mcp && go run .

And the account must be logged in:
    cd /tmp/xiaohongshu-mcp && go run cmd/login/main.go
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from nails_agent.models.schemas import RejectedTrendCandidate, TrendSignal
from nails_agent.services.tag_enricher import (
    QwenTagEnricher,
    apply_tags,
    clean_tag_dict,
    merge_tag_dict,
    rejection_reason,
    should_call_llm,
    signal_tag_dict,
)

logger = logging.getLogger(__name__)

_TZ8 = timezone(timedelta(hours=8))

# Tag vocabulary, reused from XHS Skills fetcher
_NAIL_KWS = {
    # styles
    "猫眼": "style",
    "法式": "style",
    "渐变": "style",
    "奶油": "style",
    "3D": "style",
    "贴片": "style",
    "冰透": "style",
    "暗黑": "style",
    "日式": "style",
    "韩式": "style",
    "ins风": "style",
    "极简": "style",
    "波点": "style",
    "格纹": "style",
    "花朵": "style",
    "蝴蝶": "style",
    "爱心": "style",
    "星月": "style",
    "手绘": "style",
    "光疗": "style",
    "温柔": "style",
    "高级": "style",
    "甜酷": "style",
    "复古": "style",
    # colors
    "白色": "color",
    "黑色": "color",
    "粉色": "color",
    "红色": "color",
    "蓝色": "color",
    "紫色": "color",
    "绿色": "color",
    "裸色": "color",
    "棕色": "color",
    "灰色": "color",
    "黄色": "color",
    "银色": "color",
    "金色": "color",
    "香芋": "color",
    "薄荷": "color",
    "莫兰迪": "color",
    "多巴胺": "color",
    "奶茶": "color",
    "豆沙": "color",
    # materials
    "甲油胶": "material",
    "钻": "material",
    "锡箔": "material",
    "贝壳": "material",
    "磁铁石": "material",
    "镭射": "material",
    "亮片": "material",
    "珍珠": "material",
    "金箔": "material",
    # scenes
    "新娘": "scene",
    "日常": "scene",
    "约会": "scene",
    "通勤": "scene",
    "夏日": "scene",
    "春日": "scene",
    "初春": "scene",
    "秋冬": "scene",
    "圣诞": "scene",
    "新年": "scene",
    "国庆": "scene",
    "旅游": "scene",
    "毕业": "scene",
    "婚礼": "scene",
}

_NAIL_CORE = ("美甲", "nail art", "nailart", "甲油胶", "指甲", "美甲师", "nail design")


def _make_trend_id(uid: str) -> str:
    today = datetime.now(_TZ8).strftime("%Y%m%d")
    short = hashlib.md5(uid.encode()).hexdigest()[:6].upper()
    return f"TREND_{today}_XHS_{short}"


def _safe_int(val) -> int:
    if val is None:
        return 0
    s = str(val).strip().replace(",", "")
    if not s or s == "0":
        return 0
    # Handle "1.2万" / "2.5w"
    m = re.match(r"^([\d.]+)\s*(万|w|W|千|k|K)?$", s)
    if m:
        num = float(m.group(1))
        unit = m.group(2)
        if unit in ("万", "w", "W"):
            return int(num * 10000)
        if unit in ("千", "k", "K"):
            return int(num * 1000)
        return int(num)
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _interaction_score(likes: int, collects: int, comments: int, shares: int) -> float:
    return likes + collects * 1.5 + shares * 2 + comments * 0.5


def _extract_topics(text: str) -> List[str]:
    """Extract XHS topic names from '#裸色美甲[话题]#'-style text."""
    topics: List[str] = []
    for raw in re.findall(r"#([^#]+?)#", text or ""):
        topic = re.sub(r"\[.*?\]", "", raw).strip()
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def _time_ms_to_iso(raw_time: Any) -> str:
    if raw_time in (None, ""):
        return ""
    try:
        ts = int(raw_time)
    except (TypeError, ValueError):
        return ""
    # XHS detail returns milliseconds.
    if ts > 10_000_000_000:
        ts = ts // 1000
    return datetime.fromtimestamp(ts, _TZ8).isoformat()


def _classify(text: str) -> dict:
    """Extract style/color/material/scene tags from title."""
    style, color, material, scene = [], [], [], []
    tl = text.lower()
    for kw, cat in _NAIL_KWS.items():
        if kw.lower() in tl:
            if cat == "style" and kw not in style:
                style.append(kw)
            elif cat == "color" and kw not in color:
                color.append(kw)
            elif cat == "material" and kw not in material:
                material.append(kw)
            elif cat == "scene" and kw not in scene:
                scene.append(kw)
    return {
        "style_tags": style[:5],
        "color_tags": color[:3],
        "material_tags": material[:3],
        "scene_tags": scene[:3],
    }


def _tag_confidence(classified: dict) -> float:
    meaningful = 0
    for key in ("style_tags", "color_tags", "material_tags", "scene_tags"):
        meaningful += sum(1 for tag in classified.get(key, []) if tag not in {"美甲", "nail"})
    if meaningful <= 0:
        return 0.2
    return min(0.8, round(0.35 + meaningful * 0.12, 2))


def _image_from_cover(cover: dict) -> str:
    if not isinstance(cover, dict):
        return ""
    return cover.get("urlDefault") or cover.get("url") or cover.get("urlPre") or ""


def _image_urls_from_note(note: dict) -> List[str]:
    urls: List[str] = []
    for key in ("imageList", "images", "image_list"):
        items = note.get(key) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            url = item.get("urlDefault") or item.get("url") or item.get("urlPre")
            if url and url not in urls:
                urls.append(url)
    cover_url = _image_from_cover(note.get("cover") or {})
    if cover_url and cover_url not in urls:
        urls.append(cover_url)
    return urls


def _detail_note(body: dict) -> dict:
    layers = [body]
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, dict):
        layers.append(data)
        nested = data.get("data")
        if isinstance(nested, dict):
            layers.append(nested)

    for layer in layers:
        note = layer.get("note") or layer.get("noteCard") or layer.get("note_card")
        if isinstance(note, dict):
            return note
    return {}


def _is_nail_related(text: str) -> bool:
    t = text.lower()
    if any(k in t for k in _NAIL_CORE):
        return True
    if "nail" in t:
        idx = t.find("nail")
        before = t[max(0, idx - 2) : idx]
        if not any(pre in before for pre in ("ck", "em", "de", "ai", "co", "di", "fi")):
            return True
    return False


def _feed_to_signal(feed: dict, keyword: str) -> Optional[TrendSignal]:
    """Convert one Go xhs-mcp feed item → TrendSignal."""
    try:
        nc = feed.get("noteCard", {})
        title = nc.get("displayTitle", "") or ""
        desc = nc.get("desc", "") or ""
        caption = f"{title} {desc}".strip()[:200]

        ii = nc.get("interactInfo", {})
        likes = _safe_int(ii.get("likedCount"))
        collects = _safe_int(ii.get("collectedCount"))
        comments = _safe_int(ii.get("commentCount"))
        shares = _safe_int(ii.get("sharedCount"))

        uid = feed.get("id") or nc.get("noteId") or ""
        if not uid:
            return None

        cover = nc.get("cover", {}) or {}
        cover_url = _image_from_cover(cover)

        classified = _classify(title + " " + desc)
        now_iso = datetime.now(_TZ8).isoformat()

        return TrendSignal(
            trend_id=_make_trend_id(uid),
            platform="小红书",
            keyword=keyword,
            source_title=title,
            caption=caption,
            likes=likes,
            comments=comments,
            shares=shares,
            collects=collects,
            # XHS search-feeds payload doesn't include publish time; leave
            # empty (sentinel for "unknown" → neutral recency score).
            publish_time="",
            captured_at=now_iso,
            **classified,
            image_urls=[cover_url] if cover_url else [],
            detail_enriched=False,
            source_note_id=uid,
            tag_source="rules:title",
            tag_confidence=_tag_confidence(classified),
        )
    except Exception as e:
        logger.debug("XHS-MCP parse error: %s", e)
        return None


def _merge_detail_to_signal(
    signal: TrendSignal,
    detail_body: dict,
    fallback_feed: dict,
    keyword: str,
) -> TrendSignal:
    """Merge /feeds/detail payload into a shallow search TrendSignal."""
    note = _detail_note(detail_body)
    if not note:
        return signal

    title = note.get("title") or note.get("displayTitle") or ""
    desc = note.get("desc") or ""
    topics = _extract_topics(desc)
    topic_text = " ".join(topics)
    caption = f"{title} {desc}".strip()[:500] or signal.caption
    classified = _classify(f"{title} {desc} {topic_text}")

    ii = note.get("interactInfo") or {}
    likes = _safe_int(ii.get("likedCount")) or signal.likes
    collects = _safe_int(ii.get("collectedCount")) or signal.collects
    comments = _safe_int(ii.get("commentCount")) or signal.comments
    shares = _safe_int(ii.get("sharedCount")) or signal.shares

    image_urls = _image_urls_from_note(note)
    if not image_urls:
        image_urls = list(signal.image_urls)
    if not image_urls:
        nc = fallback_feed.get("noteCard") or {}
        cover_url = _image_from_cover(nc.get("cover") or {})
        image_urls = [cover_url] if cover_url else []

    note_id = note.get("noteId") or fallback_feed.get("id") or signal.source_note_id
    publish_time = _time_ms_to_iso(note.get("time")) or signal.publish_time

    return signal.model_copy(
        update={
            "trend_id": _make_trend_id(str(note_id)) if note_id else signal.trend_id,
            "source_note_id": str(note_id or signal.source_note_id),
            "keyword": keyword,
            "source_title": title,
            "caption": caption,
            "likes": likes,
            "collects": collects,
            "comments": comments,
            "shares": shares,
            "publish_time": publish_time,
            "style_tags": classified["style_tags"],
            "color_tags": classified["color_tags"],
            "material_tags": classified["material_tags"],
            "scene_tags": classified["scene_tags"],
            "image_urls": image_urls,
            "detail_enriched": True,
            "tag_source": "rules:detail",
            "tag_confidence": _tag_confidence(classified),
        }
    )


class XHSMCPFetcher:
    """
    Fetches XHS data via the local Go xiaohongshu-mcp HTTP server.

    Two strategies:
      - search(keywords): per-keyword search via /feeds/search
      - fetch_trending(): homepage list via /feeds/list + nail-keyword filter
    """

    def __init__(self, base_url: str = "http://localhost:18060", timeout: int = 75):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._available_cache: Optional[bool] = None
        self.rejected_candidates: List[RejectedTrendCandidate] = []
        self._session = requests.Session()
        # Local MCP traffic should not be routed through HTTP_PROXY/ALL_PROXY.
        self._session.trust_env = False

    def _candidate_base_urls(self) -> List[str]:
        parsed = urlparse(self.base_url)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or "localhost"
        port = f":{parsed.port}" if parsed.port else ""
        urls = [self.base_url]
        if host in {"localhost", "127.0.0.1", "::1"}:
            for url in (
                f"{scheme}://localhost{port}",
                f"{scheme}://127.0.0.1{port}",
                f"{scheme}://[::1]{port}",
            ):
                if url not in urls:
                    urls.append(url)
        return urls

    def is_available(self, force_refresh: bool = False) -> bool:
        """Server up AND logged in.

        The check is cached because login/status may start or touch a browser.
        Long-running UI processes can pass force_refresh=True before an actual
        collection run so a previously-off MCP server can be detected after it
        comes back online.
        """
        if self._available_cache is not None and not force_refresh:
            return self._available_cache
        for base_url in self._candidate_base_urls():
            try:
                # Quick health check first (server up?)
                r = self._session.get(f"{base_url}/health", timeout=2)
                if not r.ok:
                    continue
                # Full login check (slow — starts a browser)
                r = self._session.get(f"{base_url}/api/v1/login/status", timeout=20)
                if not r.ok:
                    continue
                data = r.json().get("data") or {}
                logged_in = bool(
                    data.get("is_logged_in") or data.get("isLoggedIn") or data.get("logged_in")
                )
                if logged_in:
                    self.base_url = base_url
                    self._available_cache = True
                    return True
            except Exception as e:
                logger.debug("XHS-MCP availability check failed for %s: %s", base_url, e)
        self._available_cache = False
        return False

    def search(
        self,
        keywords: List[str],
        limit_per_kw: int = 10,
        detail_top_n: int = 10,
        detail_candidate_n: int = 15,
        detail_retry_attempts: int = 2,
        enrich_detail: bool = True,
        use_llm_tags: bool = False,
        download_images: bool = False,
        image_dir: str = "web/output/images/latest/raw",
        max_images_per_signal: int = 1,
    ) -> List[TrendSignal]:
        self.rejected_candidates = []
        if isinstance(keywords, str):
            keywords = [keywords]
        candidates: List[Tuple[TrendSignal, dict, str]] = []
        for kw in keywords:
            try:
                logger.info("XHS-MCP: searching '%s'…", kw)
                r = self._session.get(
                    f"{self.base_url}/api/v1/feeds/search",
                    params={"keyword": kw},
                    timeout=self.timeout,
                )
                if not r.ok:
                    logger.warning("XHS-MCP search '%s' HTTP %d", kw, r.status_code)
                    continue
                body = r.json()
                if not body.get("success"):
                    logger.warning("XHS-MCP search '%s' failed: %s", kw, body.get("message"))
                    continue
                feeds = (body.get("data") or {}).get("feeds") or []
                taken = 0
                for f in feeds:
                    sig = _feed_to_signal(f, kw)
                    if sig:
                        candidates.append((sig, f, kw))
                        taken += 1
                        if taken >= limit_per_kw:
                            break
                logger.info("XHS-MCP: '%s' → %d signals", kw, taken)
            except requests.Timeout:
                logger.warning("XHS-MCP timeout for '%s'", kw)
            except Exception as e:
                logger.error("XHS-MCP error for '%s': %s", kw, e)

        if not candidates:
            return []

        candidates = self._dedup_candidates(candidates)
        candidates.sort(
            key=lambda item: _interaction_score(
                item[0].likes,
                item[0].collects,
                item[0].comments,
                item[0].shares,
            ),
            reverse=True,
        )
        selected = (
            candidates[: max(detail_top_n, detail_candidate_n)] if enrich_detail else candidates
        )

        signals: List[TrendSignal] = []
        tag_enricher = QwenTagEnricher() if use_llm_tags else None

        if not enrich_detail:
            for sig, _feed, _kw in selected:
                enriched = apply_tags(sig, signal_tag_dict(sig), sig.tag_source or "rules:title")
                if download_images:
                    enriched = self._download_signal_images(
                        enriched,
                        image_dir=image_dir,
                        max_images=max_images_per_signal,
                    )
                signals.append(enriched)
            return signals

        def _process_group(group: List[Tuple[TrendSignal, dict, str]]) -> int:
            detailed: List[TrendSignal] = []
            accepted = 0
            for sig, feed, kw in group:
                detail = self.get_feed_detail(
                    feed_id=feed.get("id") or sig.source_note_id,
                    xsec_token=feed.get("xsecToken")
                    or (feed.get("noteCard") or {}).get("xsecToken")
                    or "",
                    load_all_comments=False,
                    max_attempts=detail_retry_attempts,
                )
                if not detail:
                    logger.info(
                        "XHS-MCP detail skipped after retries: feed_id=%s keyword=%s",
                        feed.get("id") or sig.source_note_id,
                        kw,
                    )
                    continue
                enriched = _merge_detail_to_signal(sig, detail, feed, kw)
                if not enriched.detail_enriched:
                    logger.info(
                        "XHS-MCP detail parse skipped: feed_id=%s keyword=%s",
                        feed.get("id") or sig.source_note_id,
                        kw,
                    )
                    continue
                enriched = apply_tags(
                    enriched,
                    signal_tag_dict(enriched),
                    enriched.tag_source or "rules:detail",
                )
                detailed.append(enriched)

            batch_tags: Dict[str, Dict[str, List[str]]] = {}
            if use_llm_tags and tag_enricher:
                need_llm = [
                    sig
                    for sig in detailed
                    if should_call_llm(signal_tag_dict(sig), sig.tag_confidence)
                ]
                if need_llm:
                    batch_tags = tag_enricher.extract_batch(need_llm)

            for enriched in detailed:
                key = enriched.source_note_id or enriched.trend_id
                llm_tags = batch_tags.get(key, {})
                if llm_tags:
                    merged = merge_tag_dict(signal_tag_dict(enriched), llm_tags)
                    source = (
                        f"{enriched.tag_source}+llm:{tag_enricher.model}"
                        if tag_enricher and any(llm_tags.values())
                        else enriched.tag_source
                    )
                    enriched = apply_tags(enriched, merged, source)
                reason = rejection_reason(signal_tag_dict(enriched))
                if reason:
                    reason_code, reason_text = reason
                    self.rejected_candidates.append(
                        self._rejected_candidate(
                            enriched,
                            reason_code=reason_code,
                            reason_text=reason_text,
                        )
                    )
                    continue
                if download_images:
                    enriched = self._download_signal_images(
                        enriched,
                        image_dir=image_dir,
                        max_images=max_images_per_signal,
                    )
                signals.append(enriched)
                accepted += 1
                if len(signals) >= detail_top_n:
                    break
            return accepted

        cursor = 0
        initial_group = selected[cursor:detail_top_n]
        cursor += len(initial_group)
        _process_group(initial_group)

        while len(signals) < detail_top_n and cursor < len(selected):
            needed = detail_top_n - len(signals)
            group = selected[cursor : cursor + needed]
            cursor += len(group)
            if not group:
                break
            _process_group(group)

        logger.info(
            "XHS-MCP: selected %d detail-enriched signals from top %d/%d candidates",
            len(signals),
            len(selected),
            len(candidates),
        )
        return signals

    @staticmethod
    def _rejected_candidate(
        signal: TrendSignal,
        *,
        reason_code: str,
        reason_text: str,
    ) -> RejectedTrendCandidate:
        tags = clean_tag_dict(signal_tag_dict(signal))
        return RejectedTrendCandidate(
            source_platform=signal.platform,
            source_note_id=signal.source_note_id,
            keyword=signal.keyword,
            source_title=signal.source_title,
            caption=signal.caption,
            style_tags=tags["style_tags"],
            color_tags=tags["color_tags"],
            material_tags=tags["material_tags"],
            scene_tags=tags["scene_tags"],
            reason_code=reason_code,
            reason_text=reason_text,
            interaction_score=_interaction_score(
                signal.likes,
                signal.collects,
                signal.comments,
                signal.shares,
            ),
            tag_source=signal.tag_source,
            tag_confidence=signal.tag_confidence,
            captured_at=signal.captured_at or datetime.now(_TZ8).isoformat(),
        )

    def get_feed_detail(
        self,
        feed_id: str,
        xsec_token: str,
        load_all_comments: bool = False,
        max_attempts: int = 2,
    ) -> Optional[Dict[str, Any]]:
        if not feed_id or not xsec_token:
            return None
        attempts = max(1, max_attempts)
        for attempt in range(1, attempts + 1):
            try:
                r = self._session.post(
                    f"{self.base_url}/api/v1/feeds/detail",
                    json={
                        "feed_id": feed_id,
                        "xsec_token": xsec_token,
                        "load_all_comments": load_all_comments,
                    },
                    timeout=self.timeout,
                )
                if not r.ok:
                    logger.warning(
                        "XHS-MCP detail '%s' HTTP %d (attempt %d/%d)",
                        feed_id,
                        r.status_code,
                        attempt,
                        attempts,
                    )
                    continue
                body = r.json()
                if body.get("success") is False:
                    logger.warning(
                        "XHS-MCP detail '%s' failed (attempt %d/%d): %s",
                        feed_id,
                        attempt,
                        attempts,
                        body.get("message"),
                    )
                    continue
                return body
            except requests.Timeout:
                logger.warning(
                    "XHS-MCP detail timeout for '%s' (attempt %d/%d)",
                    feed_id,
                    attempt,
                    attempts,
                )
            except Exception as e:
                logger.error(
                    "XHS-MCP detail error for '%s' (attempt %d/%d): %s",
                    feed_id,
                    attempt,
                    attempts,
                    e,
                )
        return None

    @staticmethod
    def _dedup_candidates(
        candidates: List[Tuple[TrendSignal, dict, str]],
    ) -> List[Tuple[TrendSignal, dict, str]]:
        seen: set[str] = set()
        deduped: List[Tuple[TrendSignal, dict, str]] = []
        for sig, feed, kw in candidates:
            key = feed.get("id") or sig.source_note_id or sig.trend_id
            if key in seen:
                continue
            seen.add(key)
            deduped.append((sig, feed, kw))
        return deduped

    def _download_signal_images(
        self,
        signal: TrendSignal,
        image_dir: str,
        max_images: int = 1,
    ) -> TrendSignal:
        if not signal.image_urls:
            return signal.model_copy(update={"image_download_status": "no_image"})

        out_dir = Path(image_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        local_paths: List[str] = []
        content_type = ""
        for idx, url in enumerate(signal.image_urls[:max_images], 1):
            try:
                r = self._session.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": "https://www.xiaohongshu.com/",
                    },
                    timeout=20,
                )
                if not r.ok or not r.content:
                    continue
                content_type = r.headers.get("Content-Type", "") or content_type
                suffix = ".webp"
                if "png" in content_type:
                    suffix = ".png"
                elif "jpeg" in content_type or "jpg" in content_type:
                    suffix = ".jpg"
                path = out_dir / f"{signal.trend_id}_{idx}{suffix}"
                path.write_bytes(r.content)
                local_paths.append(str(path))
            except Exception as exc:
                logger.debug("XHS image download failed for %s: %s", url, exc)

        return signal.model_copy(
            update={
                "local_image_paths": local_paths,
                "image_download_status": "success" if local_paths else "failed",
                "image_content_type": content_type,
            }
        )

    def fetch_trending(self, limit: int = 20) -> List[TrendSignal]:
        try:
            logger.info("XHS-MCP: fetching trending list…")
            r = self._session.get(f"{self.base_url}/api/v1/feeds/list", timeout=self.timeout)
            if not r.ok:
                logger.warning("XHS-MCP list HTTP %d", r.status_code)
                return []
            body = r.json()
            feeds = (body.get("data") or {}).get("feeds") or []
            all_sigs = [_feed_to_signal(f, "美甲") for f in feeds]
            all_sigs = [s for s in all_sigs if s and _is_nail_related(s.caption)]
            logger.info("XHS-MCP trending: %d nail-related / %d total", len(all_sigs), len(feeds))
            return all_sigs[:limit]
        except Exception as e:
            logger.error("XHS-MCP trending error: %s", e)
            return []
