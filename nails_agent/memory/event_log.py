"""
EventLog — first-class agent event log backed by MemoryStore's SQLite.

Each agent in the pipeline writes one entry per completion via EventLog.write().
The API layer reads entries via EventLog.list_by_trigger() for the SSE / polling
endpoint (GET /api/v1/events).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from nails_agent.memory.store import MemoryStore
from nails_agent.models.schemas import CandidatePackage, EventLogEntry, ReviewDecision


class EventLog:
    def __init__(self, db_path: Optional[Path] = None):
        self._store = MemoryStore(db_path=db_path)

    # ── Write ─────────────────────────────────────────────────────────────────

    def write(
        self,
        event_type: str,
        payload: Dict[str, Any],
        trigger_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> EventLogEntry:
        entry = EventLogEntry(
            event_type=event_type,
            trigger_id=trigger_id,
            agent_id=agent_id,
            payload=payload,
        )
        with self._store._conn() as conn:
            conn.execute(
                """INSERT INTO event_log (id, event_type, trigger_id, agent_id, payload, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry.id,
                    entry.event_type,
                    entry.trigger_id,
                    entry.agent_id,
                    json.dumps(entry.payload, ensure_ascii=False),
                    entry.created_at,
                ),
            )
        return entry

    # ── Read ──────────────────────────────────────────────────────────────────

    def list_by_trigger(
        self,
        trigger_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EventLogEntry]:
        with self._store._conn() as conn:
            rows = conn.execute(
                """SELECT id, event_type, trigger_id, agent_id, payload, created_at
                   FROM event_log
                   WHERE trigger_id = ?
                   ORDER BY created_at ASC
                   LIMIT ? OFFSET ?""",
                (trigger_id, limit, offset),
            ).fetchall()
        return [
            EventLogEntry(
                id=r["id"],
                event_type=r["event_type"],
                trigger_id=r["trigger_id"],
                agent_id=r["agent_id"],
                payload=json.loads(r["payload"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def list_recent(self, limit: int = 50) -> List[EventLogEntry]:
        with self._store._conn() as conn:
            rows = conn.execute(
                """SELECT id, event_type, trigger_id, agent_id, payload, created_at
                   FROM event_log
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [
            EventLogEntry(
                id=r["id"],
                event_type=r["event_type"],
                trigger_id=r["trigger_id"],
                agent_id=r["agent_id"],
                payload=json.loads(r["payload"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # ── Candidate Packages ────────────────────────────────────────────────────

    def save_candidate(self, pkg: CandidatePackage) -> None:
        with self._store._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO candidate_packages
                   (id, trigger_id, content, review_status, created_at)
                   VALUES (?, ?, ?, 'pending_review', ?)""",
                (
                    pkg.id,
                    pkg.trigger_id,
                    pkg.model_dump_json(),
                    pkg.created_at,
                ),
            )

    def get_candidate(self, trigger_id: str) -> Optional[CandidatePackage]:
        with self._store._conn() as conn:
            row = conn.execute(
                """SELECT content FROM candidate_packages
                   WHERE trigger_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (trigger_id,),
            ).fetchone()
        if not row:
            return None
        return CandidatePackage.model_validate_json(row["content"])

    def update_candidate_review(
        self,
        trigger_id: str,
        decision: ReviewDecision,
        status: str,
    ) -> None:
        with self._store._conn() as conn:
            conn.execute(
                """UPDATE candidate_packages
                   SET review_status = ?, review_output = ?
                   WHERE trigger_id = ?""",
                (
                    status,
                    decision.model_dump_json(),
                    trigger_id,
                ),
            )
