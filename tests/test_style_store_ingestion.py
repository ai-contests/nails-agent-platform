from __future__ import annotations

from nails_agent.memory.store import MemoryStore
from nails_agent.models.schemas import (
    CampaignStrategyResult,
    PublishSchedule,
    StyleCard,
    TrendAnalysisResult,
    TrendSignal,
)
from nails_agent.services.style_store_ingestion import ingest_campaign_styles


def _signal(trend_id: str) -> TrendSignal:
    return TrendSignal(
        trend_id=trend_id,
        platform="xhs",
        keyword="美甲推荐",
        source_title="冰透猫眼美甲",
        caption="冰透猫眼 约会通勤都适合",
        likes=100,
        collects=40,
        shares=10,
        comments=5,
        style_tags=["猫眼"],
        color_tags=["冰透粉"],
        material_tags=["亮片"],
        scene_tags=["约会"],
        local_image_paths=["data/images/mock/raw/demo.webp"],
        composite_score=88.0,
        rank=1,
    )


def _card(trend_id: str, style_id: str, priority: str) -> StyleCard:
    return StyleCard(
        trend_id=trend_id,
        style_id=style_id,
        style_name="趋势样本",
        style_tags=["猫眼"],
        image_url="data/images/mock/raw/demo.webp",
        schedule=PublishSchedule(priority=priority),
    )


def test_ingest_campaign_styles_writes_p0_p1_to_json_and_memory(tmp_path):
    memory = MemoryStore(db_path=tmp_path / "memory.db")
    analysis = TrendAnalysisResult(
        top_10=[_signal("TREND_A"), _signal("TREND_B"), _signal("TREND_C")],
        patterns=[],
        anomalies=[],
    )
    campaign = CampaignStrategyResult(
        style_cards=[
            _card("TREND_A", "STYLE_A", "P0"),
            _card("TREND_B", "STYLE_B", "P1"),
            _card("TREND_C", "STYLE_C", "P2"),
        ]
    )

    result = ingest_campaign_styles(
        analysis,
        campaign,
        memory=memory,
        data_dir=tmp_path,
        extract_visual_features=False,
        analyze_reference_hand=False,
    )

    assert [item["style_id"] for item in result["styles"]] == ["STYLE_A", "STYLE_B"]
    assert memory.get_style("STYLE_A")["color_tags"] == ["冰透粉"]
    assert memory.get_style("STYLE_C") is None

    store_text = (tmp_path / "nail_styles_store.json").read_text(encoding="utf-8")
    assert "STYLE_A" in store_text
    assert "STYLE_C" not in store_text
