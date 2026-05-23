"""Tag enrichment for real trend candidates.

Mock data is expected to arrive with completed tags. This module is used on
real crawler/detail payloads before they enter the four-step pipeline.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Tuple

import requests

from nails_agent.models.schemas import TrendSignal
from nails_agent.services.llm_config import tag_llm_config


logger = logging.getLogger(__name__)

TAG_FIELDS = ("style_tags", "color_tags", "material_tags", "scene_tags")
PROMPT_VERSION = "tag_extract_v1"

_DROP_TAGS = {
    "",
    "美甲",
    "指甲",
    "款式",
    "款",
    "图",
    "图片",
    "合集",
    "教程",
    "步骤",
    "分享",
    "推荐",
    "种草",
    "热门",
    "爆款",
    "好看",
    "绝了",
    "高级感",
    "显白",
    "百搭",
    "出片",
    "适合拍照",
    "亲手晒美甲",
}
_DROP_CONTAINS = ("教程", "步骤", "怎么", "分享", "推荐", "合集", "晒美甲", "选美甲")
_TAG_LIMITS = {
    "style_tags": 5,
    "color_tags": 4,
    "material_tags": 4,
    "scene_tags": 4,
}


def _strip_topic_markup(value: str) -> str:
    value = re.sub(r"\[.*?\]", "", value)
    value = value.strip(" #，,。.!！?？:：;；、|｜/\\\t\n\r")
    return value


def clean_tag(tag: Any) -> str:
    raw = _strip_topic_markup(str(tag or "").strip())
    if not raw:
        return ""
    raw = raw.replace("nail art", "nail").replace("Nail Art", "nail")
    if raw.endswith("美甲") and len(raw) > 2:
        raw = raw[:-2]
    if raw.startswith("美甲") and len(raw) > 2:
        raw = raw[2:]
    raw = _strip_topic_markup(raw)
    if not raw:
        return ""
    lower = raw.lower()
    if lower in {"nail", "nails", "nailart", "naildesign"}:
        return ""
    if raw in _DROP_TAGS:
        return ""
    if any(part in raw for part in _DROP_CONTAINS):
        return ""
    # Tags should be compact concepts, not phrases/sentences.
    if len(raw) > 8:
        return ""
    return raw


def clean_tag_dict(raw: Dict[str, Any]) -> Dict[str, List[str]]:
    cleaned: Dict[str, List[str]] = {}
    for field in TAG_FIELDS:
        items = raw.get(field) if isinstance(raw, dict) else []
        if not isinstance(items, list):
            items = []
        values: List[str] = []
        for item in items:
            tag = clean_tag(item)
            if tag and tag not in values:
                values.append(tag)
            if len(values) >= _TAG_LIMITS[field]:
                break
        cleaned[field] = values
    return cleaned


def signal_tag_dict(signal: TrendSignal) -> Dict[str, List[str]]:
    return {field: list(getattr(signal, field, []) or []) for field in TAG_FIELDS}


def effective_tag_count(tags: Dict[str, List[str]]) -> int:
    return sum(len(clean_tag_dict(tags).get(field, [])) for field in TAG_FIELDS)


def empty_tag_category_count(tags: Dict[str, List[str]]) -> int:
    cleaned = clean_tag_dict(tags)
    return sum(1 for field in TAG_FIELDS if not cleaned.get(field))


def tag_confidence(tags: Dict[str, List[str]]) -> float:
    count = effective_tag_count(tags)
    if count <= 0:
        return 0.2
    return min(0.9, round(0.35 + count * 0.12, 2))


def should_call_llm(tags: Dict[str, List[str]], confidence: float) -> bool:
    return confidence <= 0.7 or empty_tag_category_count(tags) >= 2


def rejection_reason(tags: Dict[str, List[str]]) -> Tuple[str, str] | None:
    cleaned = clean_tag_dict(tags)
    if not cleaned["style_tags"] and not cleaned["color_tags"]:
        return "no_style_and_color", "规则与 LLM 后 style_tags 和 color_tags 同时为空"
    if effective_tag_count(cleaned) <= 1:
        return "insufficient_effective_tags", "规则与 LLM 后有效标签总数小于等于 1"
    return None


def merge_tag_dict(base: Dict[str, List[str]], extra: Dict[str, List[str]]) -> Dict[str, List[str]]:
    merged: Dict[str, List[str]] = {}
    base = clean_tag_dict(base)
    extra = clean_tag_dict(extra)
    for field in TAG_FIELDS:
        values = list(base.get(field, []))
        for tag in extra.get(field, []):
            if tag not in values:
                values.append(tag)
            if len(values) >= _TAG_LIMITS[field]:
                break
        merged[field] = values
    return merged


def apply_tags(signal: TrendSignal, tags: Dict[str, List[str]], source: str) -> TrendSignal:
    cleaned = clean_tag_dict(tags)
    return signal.model_copy(
        update={
            **cleaned,
            "tag_source": source,
            "tag_confidence": tag_confidence(cleaned),
        }
    )


class QwenTagEnricher:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 30,
    ):
        config = tag_llm_config(model=model, api_key=api_key, base_url=base_url)
        self.model = config.model
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url)

    def extract(self, signal: TrendSignal) -> Dict[str, List[str]]:
        empty = {field: [] for field in TAG_FIELDS}
        return self.extract_batch([signal]).get(signal.source_note_id or signal.trend_id, empty)

    def extract_batch(self, signals: List[TrendSignal]) -> Dict[str, Dict[str, List[str]]]:
        if not self.available:
            return {}
        if not signals:
            return {}

        prompt = self._batch_prompt(signals)
        try:
            payload = {
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是美甲趋势标签抽取器。只基于用户提供的 source_title 和 "
                            "caption 提取明确出现或强相关的美甲特征标签。不要为了补齐字段"
                            "而推测，不确定就留空。只输出 JSON，不要解释。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            }
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            if not resp.ok:
                if "response_format" in resp.text:
                    retry_payload = dict(payload)
                    retry_payload.pop("response_format", None)
                    resp = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=retry_payload,
                        timeout=self.timeout,
                    )
                if not resp.ok:
                    logger.warning(
                        "Qwen tag extraction HTTP %d: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return {}
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = self._parse_json(content)
            return self._parse_batch_result(parsed)
        except Exception as exc:
            logger.warning("Qwen tag extraction failed: %s", exc)
            return {}

    def _prompt(self, signal: TrendSignal) -> str:
        return (
            f"source_title:\n{signal.source_title or ''}\n\n"
            f"caption:\n{signal.caption or ''}\n\n"
            "请抽取四类标签，字段固定为 style_tags、color_tags、material_tags、scene_tags。\n"
            "要求：\n"
            "1. 只抽取原文明确提到或强相关的短标签，不要创造新概念。\n"
            "2. 不要输出“美甲、好看、显白、推荐、教程、分享、合集、爆款、种草”等泛词。\n"
            "3. 如果某类没有明确依据，返回空数组。\n"
            "4. 每个标签尽量为 2-4 个汉字的短词，例如“法式、猫眼、裸色、亮片、约会”。\n"
            "5. 只返回 JSON，例如：\n"
            '{"style_tags":["法式"],"color_tags":["裸色"],"material_tags":[],"scene_tags":[]}'
        )

    def _batch_prompt(self, signals: List[TrendSignal]) -> str:
        items = [
            {
                "source_note_id": s.source_note_id or s.trend_id,
                "source_title": s.source_title or "",
                "caption": s.caption or "",
            }
            for s in signals
        ]
        return (
            "请为 items 中每条美甲内容分别抽取四类标签。\n"
            "字段固定为 style_tags、color_tags、material_tags、scene_tags。\n"
            "要求：\n"
            "1. 只抽取每条原文明确提到或强相关的短标签，不要创造新概念。\n"
            "2. 不要输出“美甲、好看、显白、推荐、教程、分享、合集、爆款、种草”等泛词。\n"
            "3. 如果某类没有明确依据，返回空数组。\n"
            "4. 每个标签尽量为 2-4 个汉字的短词，例如“法式、猫眼、裸色、亮片、约会”。\n"
            "5. 必须保留每条输入的 source_note_id，用它对齐结果；不要靠顺序。\n"
            "6. 只返回 JSON，格式如下：\n"
            '{"items":[{"source_note_id":"xxx","style_tags":[],"color_tags":[],"material_tags":[],"scene_tags":[]}]}\n\n'
            f"items:\n{json.dumps(items, ensure_ascii=False, indent=2)}"
        )

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _parse_batch_result(parsed: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
        raw_items = parsed.get("items")
        if raw_items is None and any(field in parsed for field in TAG_FIELDS):
            raw_items = [parsed]
        if not isinstance(raw_items, list):
            return {}
        results: Dict[str, Dict[str, List[str]]] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            source_note_id = str(item.get("source_note_id") or item.get("trend_id") or "").strip()
            if not source_note_id:
                continue
            results[source_note_id] = clean_tag_dict(item)
        return results


def enrich_signal_tags(
    signal: TrendSignal,
    *,
    use_llm: bool,
    enricher: QwenTagEnricher | None = None,
) -> TrendSignal:
    rule_tags = clean_tag_dict(signal_tag_dict(signal))
    confidence = tag_confidence(rule_tags)
    source = signal.tag_source or "rules"
    if use_llm and should_call_llm(rule_tags, confidence):
        enricher = enricher or QwenTagEnricher()
        llm_tags = enricher.extract(signal)
        merged = merge_tag_dict(rule_tags, llm_tags)
        source = f"{source}+llm:{enricher.model}" if any(llm_tags.values()) else source
        return apply_tags(signal, merged, source)
    return apply_tags(signal, rule_tags, source)
