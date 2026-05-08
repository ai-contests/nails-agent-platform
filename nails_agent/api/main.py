"""
FastAPI application — Nails Agent Platform.

Endpoints:
  POST /chat           — natural-language trigger for pipeline runs
  POST /pipeline/run   — explicit full pipeline trigger
  POST /pipeline/trend — step 1 only (trend analysis)
  GET  /pipeline/{id}  — pipeline state query
  GET  /pipeline/list  — recent pipeline runs
  POST /tryon          — ComfyUI style try-on
  GET  /styles         — style library listing
  GET  /health         — health check
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from nails_agent.models.schemas import (
    ChatRequest,
    ChatResponse,
    TryOnRequest,
    TryOnResponse,
    PipelineState,
    StyleLibraryItem,
)
from nails_agent.memory.store import MemoryStore
from nails_agent.agents.orchestrator import PipelineOrchestrator

app = FastAPI(
    title="Nails Agent Platform",
    description="AI-powered nail trend analysis and campaign strategy",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons ────────────────────────────────────────────────────────────────

_memory: Optional[MemoryStore] = None
_orchestrator: Optional[PipelineOrchestrator] = None

DATA_DIR = os.environ.get("NAILS_DATA_DIR", "demo/data")
OUTPUT_DIR = os.environ.get("NAILS_OUTPUT_DIR", "demo/output")
WORKFLOW_PATH = Path(os.environ.get(
    "NAILS_WORKFLOW_PATH",
    "/Users/nev4rb14su/Downloads/image_flux2_klein_image_edit_9b_base.json"
))
HAND_REF_PATH = Path(DATA_DIR).parent / "static" / "hand_reference.jpg"
NAIL_REF_PATH = Path(DATA_DIR).parent / "static" / "nail_reference.jpg"


def get_memory() -> MemoryStore:
    global _memory
    if _memory is None:
        _memory = MemoryStore()
    return _memory


def get_orchestrator() -> PipelineOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator(
            memory=get_memory(),
            data_dir=DATA_DIR,
            output_dir=OUTPUT_DIR,
        )
    return _orchestrator


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    orch = get_orchestrator()
    sources = orch.source_status()
    return {"status": "ok", "version": "0.2.0", "data_sources": sources}


@app.get("/sources")
async def sources():
    """Check which real data sources are available."""
    orch = get_orchestrator()
    return orch.source_status()


# ── Chat ──────────────────────────────────────────────────────────────────────

_TRIGGER_KEYWORDS = {
    "趋势": "trend",
    "trend": "trend",
    "运营": "full",
    "pipeline": "full",
    "完整": "full",
    "full": "full",
}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    msg = req.message.lower()

    action = None
    for kw, act in _TRIGGER_KEYWORDS.items():
        if kw in msg:
            action = act
            break

    if action == "trend":
        orch = get_orchestrator()
        messages = []
        state = orch.run_step1_only(progress_cb=messages.append)
        return ChatResponse(
            reply=f"✅ 趋势分析完成！Top 3：{', '.join(s.keyword for s in (state.trend_analysis.top_10[:3] if state.trend_analysis else []))}",
            pipeline_id=state.pipeline_id,
        )

    if action == "full":
        orch = get_orchestrator()
        messages = []
        state = orch.run(progress_cb=messages.append)
        top3 = state.report.top_3_keywords if state.report else []
        return ChatResponse(
            reply=f"✅ 完整流水线完成！Top 3 关键词：{', '.join(top3)}。共 {state.report.total_style_cards if state.report else 0} 张运营卡片。",
            pipeline_id=state.pipeline_id,
            state={"status": state.status, "step": state.step},
        )

    return ChatResponse(
        reply="你好！发送「趋势分析」运行 Step 1，发送「完整运营」运行全流水线。",
    )


# ── Pipeline endpoints ────────────────────────────────────────────────────────

class PipelineRunResponse(BaseModel):
    pipeline_id: str
    status: str
    message: str
    state: Optional[Dict[str, Any]] = None


@app.post("/pipeline/run", response_model=PipelineRunResponse)
async def pipeline_run():
    orch = get_orchestrator()
    state = orch.run()
    return PipelineRunResponse(
        pipeline_id=state.pipeline_id,
        status=state.status,
        message=f"Pipeline {'完成' if state.status == 'done' else '失败'}",
        state={"step": state.step, "errors": state.errors},
    )


@app.post("/pipeline/trend", response_model=PipelineRunResponse)
async def pipeline_trend():
    orch = get_orchestrator()
    state = orch.run_step1_only()
    return PipelineRunResponse(
        pipeline_id=state.pipeline_id,
        status=state.status,
        message="趋势分析完成" if state.status == "done" else "趋势分析失败",
    )


@app.get("/pipeline/list")
async def pipeline_list(limit: int = 20):
    return get_memory().list_pipeline_runs(limit=limit)


@app.get("/pipeline/{pipeline_id}")
async def pipeline_get(pipeline_id: str):
    result = get_memory().get_pipeline_state(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


# ── Memory search ─────────────────────────────────────────────────────────────

@app.get("/memory/search")
async def memory_search(q: str, kind: Optional[str] = None, limit: int = 10):
    results = get_memory().search(q, kind=kind, limit=limit)
    return [r.model_dump() for r in results]


@app.get("/memory/insights")
async def memory_insights(limit: int = 20):
    results = get_memory().list_recent("insight", limit=limit)
    return [r.model_dump() for r in results]


# ── Style library ─────────────────────────────────────────────────────────────

@app.get("/styles")
async def list_styles():
    path = Path(DATA_DIR) / "style_library.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Try-on ────────────────────────────────────────────────────────────────────

@app.post("/tryon", response_model=TryOnResponse)
async def tryon(req: TryOnRequest):
    import time
    t0 = time.time()

    # Resolve style image
    style_path = str(NAIL_REF_PATH)
    lib_path = Path(DATA_DIR) / "style_library.json"
    if lib_path.exists():
        with open(lib_path, encoding="utf-8") as f:
            library = json.load(f)
        for item in library:
            if item.get("style_id") == req.style_id:
                candidate = item.get("image_url", "")
                if candidate and Path(candidate).exists():
                    style_path = candidate
                break

    # Load workflow
    if not WORKFLOW_PATH.exists():
        return TryOnResponse(
            success=False,
            error=f"Workflow not found: {WORKFLOW_PATH}",
            fallback_url=str(NAIL_REF_PATH),
        )

    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        workflow = json.load(f)

    # Run via ComfyUI client
    try:
        from nails_agent.tools.comfyui_client import ComfyUIClient
        client = ComfyUIClient()
        result = client.run_tryon(
            workflow=workflow,
            hand_image_path=str(HAND_REF_PATH),
            style_image_path=style_path,
        )
        return TryOnResponse(
            success=result["success"],
            image_url=result.get("image_url"),
            fallback_url=str(NAIL_REF_PATH),
            error=result.get("error"),
            duration_s=result.get("duration_s", round(time.time() - t0, 1)),
        )
    except Exception as exc:
        return TryOnResponse(
            success=False,
            error=str(exc),
            fallback_url=str(NAIL_REF_PATH),
            duration_s=round(time.time() - t0, 1),
        )
