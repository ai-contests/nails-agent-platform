"""Presentation helpers for trend samples.

These functions keep collection metadata (search keywords) separate from the
business-facing sample labels shown in UI, reports, and strategy cards.
"""

from __future__ import annotations

from typing import Any, Iterable, List


_NOISE_TAGS = {
    "美甲",
    "美甲推荐",
    "美甲灵感",
    "美甲教程",
    "高级美甲",
    "显白美甲",
    "nail",
    "nailart",
}


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _iter_tags(signal: Any) -> Iterable[str]:
    for field in ("style_tags", "color_tags", "material_tags", "scene_tags"):
        for tag in _get(signal, field, []) or []:
            yield str(tag).strip()


def signal_tags(signal: Any, max_tags: int = 5) -> List[str]:
    tags: List[str] = []
    for tag in _iter_tags(signal):
        if not tag or tag.lower() in _NOISE_TAGS or tag in tags:
            continue
        tags.append(tag)
        if len(tags) >= max_tags:
            break
    return tags


def tag_summary(signal: Any, max_tags: int = 5, empty: str = "待补充标签") -> str:
    tags = signal_tags(signal, max_tags=max_tags)
    return " / ".join(tags) if tags else empty


def sample_label(signal: Any, rank: int | None = None, with_tags: bool = True) -> str:
    base = _get(signal, "display_label", "") or ""
    if not base:
        sample_no = rank or _get(signal, "rank", 0) or 0
        base = f"样本 {int(sample_no):02d}" if sample_no else "趋势样本"
    if not with_tags:
        return base
    tags = tag_summary(signal, max_tags=3, empty="")
    return f"{base} · {tags}" if tags else base


def source_title(signal: Any, max_len: int = 32) -> str:
    title = _get(signal, "source_title", "") or ""
    if not title:
        caption = _get(signal, "caption", "") or ""
        title = caption.split("#", 1)[0].strip().replace("\n", " ")
    if len(title) > max_len:
        return title[:max_len] + "..."
    return title


def signal_image_url(signal: Any) -> str:
    for field in ("local_image_paths", "image_urls"):
        urls = _get(signal, field, []) or []
        if urls:
            return str(urls[0])
    return ""
