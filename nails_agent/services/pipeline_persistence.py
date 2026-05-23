"""Shared persistence helpers for B-end pipeline runs.

Both the one-shot FastAPI pipeline and the Streamlit step-review runner should
write the same artifacts and SQLite rows.  Keeping that logic here prevents the
two entry points from quietly drifting apart.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from nails_agent.memory.store import MemoryStore
from nails_agent.models.schemas import (
    AssetGenerationResult,
    CampaignStrategyResult,
    MemoryEntry,
    PipelineState,
    RejectedTrendCandidate,
    SummaryReport,
    TrendAnalysisResult,
    TrendSignal,
    ValueEvaluationResult,
)

logger = logging.getLogger(__name__)


class PipelinePersistence:
    """Persist pipeline artifacts to `web/output` and `MemoryStore`."""

    def __init__(
        self,
        memory: Optional[MemoryStore] = None,
        output_dir: str | Path = "web/output",
    ):
        self.memory = memory or MemoryStore()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: PipelineState) -> None:
        self.memory.save_pipeline_state(
            state.pipeline_id,
            state.status,
            state.model_dump_json(),
        )

    def save_checkpoint(
        self,
        state: PipelineState,
        phase: str,
        checkpoint_id: str = "",
        status: str = "waiting_review",
    ) -> None:
        state.status = status
        state.meta.update(
            {
                "phase": phase,
                "checkpoint_id": checkpoint_id or phase,
                "persisted_at": datetime.now().isoformat(),
            }
        )
        self.save_state(state)

    def persist_signals(self, signals: List[TrendSignal]) -> None:
        try:
            path = self.output_dir / "trend_signals.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump([s.model_dump() for s in signals], f, ensure_ascii=False, indent=2)
            logger.debug("Persisted %d signals to %s", len(signals), path)
        except Exception as exc:
            logger.warning("Failed to persist signals: %s", exc)

    def persist_rejected_candidates(
        self,
        pipeline_id: str,
        candidates: List[RejectedTrendCandidate],
    ) -> None:
        try:
            enriched = [c.model_copy(update={"pipeline_id": pipeline_id}) for c in candidates]
            self.memory.save_rejected_trend_candidates(enriched, pipeline_id=pipeline_id)
            path = self.output_dir / "rejected_trend_candidates.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump([c.model_dump() for c in enriched], f, ensure_ascii=False, indent=2)
            logger.debug("Persisted %d rejected candidates to %s", len(enriched), path)
        except Exception as exc:
            logger.warning("Failed to persist rejected candidates: %s", exc)

    def persist_trend_analysis(self, pipeline_id: str, result: TrendAnalysisResult) -> None:
        entries: List[MemoryEntry] = []
        for sig in result.top_10:
            entries.append(
                MemoryEntry(
                    pipeline_id=pipeline_id,
                    produced_by="trend_analyst",
                    kind="trend",
                    key=sig.trend_id,
                    value=sig.model_dump_json(),
                    tags=f"{sig.keyword},{','.join(sig.style_tags)},{sig.platform}",
                )
            )
        for i, pattern in enumerate(result.patterns):
            entries.append(
                MemoryEntry(
                    pipeline_id=pipeline_id,
                    produced_by="trend_analyst",
                    kind="pattern",
                    key=f"pattern_{i}",
                    value=pattern,
                    tags=pattern,
                )
            )
        for i, anomaly in enumerate(result.anomalies):
            entries.append(
                MemoryEntry(
                    pipeline_id=pipeline_id,
                    produced_by="trend_analyst",
                    kind="anomaly",
                    key=f"anomaly_{i}",
                    value=anomaly,
                    tags=anomaly,
                )
            )
        self.memory.save_many(entries)
        (self.output_dir / "trend_top10.json").write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def persist_value_evaluation(self, pipeline_id: str, result: ValueEvaluationResult) -> None:
        entries = [
            MemoryEntry(
                pipeline_id=pipeline_id,
                produced_by="value_evaluator",
                kind="metric",
                key=s.metric_id,
                value=s.model_dump_json(),
                tags=f"{s.keyword},priority:{s.launch_priority_score:.0f}",
            )
            for s in result.snapshots
        ]
        self.memory.save_many(entries)
        (self.output_dir / "metric_snapshots.json").write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def persist_asset_generation(self, pipeline_id: str, result: AssetGenerationResult) -> None:
        entries = [
            MemoryEntry(
                pipeline_id=pipeline_id,
                produced_by="asset_generator",
                kind="style_card_draft",
                key=d.card_id,
                value=d.model_dump_json(),
                tags=f"{d.style_name},{','.join(d.style_tags)}",
            )
            for d in result.drafts
        ]
        self.memory.save_many(entries)
        (self.output_dir / "style_cards_draft.json").write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def persist_campaign(self, pipeline_id: str, result: CampaignStrategyResult) -> None:
        entries = [
            MemoryEntry(
                pipeline_id=pipeline_id,
                produced_by="campaign_strategist",
                kind="style_card",
                key=c.card_id,
                value=c.model_dump_json(),
                tags=f"{c.style_name},priority:{c.schedule.priority if c.schedule else 'P2'}",
            )
            for c in result.style_cards
        ]
        self.memory.save_many(entries)
        (self.output_dir / "style_cards.json").write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def persist_report(self, pipeline_id: str, report: SummaryReport) -> None:
        entry = MemoryEntry(
            pipeline_id=pipeline_id,
            produced_by="summarizer",
            kind="summary",
            key=pipeline_id,
            value=report.model_dump_json(),
            tags=",".join(report.top_3_keywords),
        )
        self.memory.save(entry)
        (self.output_dir / "report.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def write_report_markdown(self, markdown: str) -> None:
        (self.output_dir / "report.md").write_text(markdown, encoding="utf-8")
