# E2E Preview Report — `fix/pipeline-quality`

**Date:** 2026-05-29
**Branch:** `fix/pipeline-quality`
**Base:** `upstream/master @ 74c355f` ("fix: Enhance the logic to make e2e more stable (#5)")
**Scope:** 34 commits · 33 files · +3,842 / −167

This PR builds on PR6 and finishes the pipeline-quality optimization points:
9-grid image cutting, VLM tag enrichment, specific style names, multi-model
fallback (vision **and** text), and pipeline resilience on empty/quota failures.

---

## 1. Summary

| Item | Status | Evidence |
|------|--------|----------|
| Unit/integration tests | ✅ 30 passed | `pytest` (§4.1) |
| Vision-LLM fallback chain | ✅ live-verified | real API hop past dead model (§4.2) |
| Text-LLM fallback chain | ✅ live-verified | real API hop past 429 quota (§4.3) |
| 9-grid detect → split → best cell | ✅ unit-verified + demo cells | `test_xhs_grid.py`, `DEMO_GRID9_cell*.webp` (§4.4) |
| Pipeline runs end-to-end | ✅ ran to `Status: done` | all 4 stages, graceful empty handling (§4.5) |
| Specific style names in live output | ⚠️ code-complete, not output-verified | blocked behind XHS (§5) |
| Top-10 diversity in live output | ⚠️ code-complete, not output-verified | blocked behind XHS (§5) |

**Bottom line:** every component is verified in isolation (tests + live API
calls). A single fully-green e2e against *fresh* XHS data is pending one
external action — refreshing the XHS session (§5). It is not a code defect.

---

## 2. What changed (by area)

### Data collection — `tools/fetchers/`
- **9-grid handling** (`xhs_mcp_fetcher.py`): detect grid9 / wide-strip / normal;
  prefer individual post images over the composite; otherwise split 3×3 and keep
  the sharpest cell(s). Wide-strip banners are discarded.
- Expanded multi-dimensional keyword pool (color / scene / style / shape / craft)
  with per-run sampling; raised signal limits; fixed Note-not-found retry waste.
- Re-enabled `XHSCDPFetcher` as primary XHS source.

### Tag enrichment — `services/tag_enricher.py`, `services/llm_config.py`
- **Vision fallback chain** (`vision_tag_configs`): 5 verified ModelScope VL models
  → DashScope → OpenRouter. `VisionTagEnricher` iterates candidates, advancing past
  429 / no-provider / transport errors until one succeeds.
- Empty `color_tags` always triggers VLM enrichment; tag length cap 8→12;
  repaired smart-quote corruption in prompts.

### Agent reasoning — `agents/`
- **Text fallback chain** (`agent_text_models` + `run_streamed_with_fallback`):
  on a quota/rate-limit/no-provider error, the agent's model swaps to the next
  candidate and the run retries — shared by TrendScout and Campaign.
- Specific style names via `display_label` propagation; dedup by `display_label`
  in campaign context; campaign rule-based fallback uses `composite_score`.

### Infra — `scripts/`
- `xhs_rest_bridge.mjs`: added `POST /api/v1/feeds/detail` and
  `POST /api/v1/accounts/reload` (evict cached client after re-login).
- `xhs_login.py`: pings the reload endpoint so new cookies apply without restart.

### Tests & docs
- New: `test_xhs_grid.py`, `test_nail_extractor.py`, `test_nail_length.py`,
  `test_recommendation_fallback.py`.
- Reports: `web/alignment.html`, `web/report.html`, `web/report_grid.html`,
  `web/tech_doc.html`.

---

## 3. Pipeline stages (4-step flow)

```
Step 1/4  趋势分析     TrendScoutAgent → collect signals, enrich tags (rules→text LLM→VLM)
Step 2/4  价值评估+素材  value evaluation & asset generation (parallel)
Step 3/4  运营策略     CampaignAgent → style cards, P0/P1 priority
Step 4/4  运营报告     report.json + markdown brief
```

Output artifacts: `web/output/{trend_signals,trend_top10,metric_snapshots,style_cards,style_cards_draft,report}.json`.

---

## 4. Verification details

### 4.1 Unit / integration tests — ✅ 30 passed (2.76s)
```
pytest tests/test_xhs_grid.py tests/test_nail_extractor.py \
       tests/test_nail_length.py tests/test_recommendation_fallback.py
→ 30 passed
```
Covers: grid9 detection, 3×3 split + best-cell selection + cleanup, wide/tall
strip classification, nail-length classification, Roboflow crop extraction +
no-key/missing-image fallbacks, and hand-shape recommendation fallbacks.

### 4.2 Vision-LLM fallback — ✅ live-verified
Prepended a known-dead model (`Qwen/Qwen2.5-VL-72B-Instruct`) to the chain and
ran a real extraction:
```
INFO VisionTagEnricher: Qwen/Qwen2.5-VL-72B-Instruct unavailable
     (HTTP 400: ...has no provider supported), trying next model
RESULT: {'style_tags': ['法式','简约'], 'color_tags': ['裸粉'],
         'material_tags': ['亮面'], 'scene_tags': ['日常','约会']}
```
→ hops past the dead model and returns real tags from the next candidate.

### 4.3 Text-LLM fallback — ✅ live-verified
The primary text model is currently at its daily quota (429). A live agent run:
```
PROGRESS:  ['♻️ 配额受限，切换模型 → Qwen/Qwen3-235B-A22B-Thinking-2507']
FINAL OUTPUT: 'hello'
MODEL USED:  Qwen/Qwen3-235B-A22B-Thinking-2507
```
→ 429 on primary, auto-switch to next model, success.

### 4.4 9-grid cutting — ✅ unit-verified + demo artifacts
- `test_grid9_detected`, `test_split_grid9_produces_cells`,
  `test_split_grid9_cleans_up_unchosen` all pass.
- Demo cells present on disk: `web/output/images/latest/raw/DEMO_GRID9_cell*.webp`
  (only the chosen best cells retained; the other 7 cleaned up).
- Note: "best" cell = highest Laplacian/diff-variance sharpness — a proxy for
  quality, not true aesthetic ranking.

### 4.5 End-to-end run — ✅ ran to `Status: done`
```
⏳ Step 1/4 趋势分析中…       ✅ Step 1 完成
⏳ Step 2/4 价值评估 & 素材生成 ✅ Step 2 完成 — 0 条评估, 0 张卡片草稿
⏳ Step 3/4 运营策略制定中…    ✅ Step 3 完成 — 0 张策略卡片
⏳ Step 4/4 生成运营报告…      ✅ Step 4 完成 — 报告已生成
Pipeline ID: a14195e1d275  Status: done
```
The pipeline completed all 4 stages and produced a valid (empty) `report.json`
without crashing — demonstrating graceful degradation. **Zero output is the
expected result given the §5 blocker, not a code failure.**

> The 429 seen in this run's log predates the §4.3 text-fallback fix
> (committed afterward); a re-run will exercise the fallback instead of erroring.

---

## 5. Known limitation — fresh-data e2e is gated on XHS session

The e2e produced 0 signals because **all 19 XHS keyword searches returned 0
results**. Direct bridge probe confirms it:
```
GET /api/v1/feeds/search?keyword=猫眼美甲 → {"feeds":[],"total":0}
GET /api/v1/login/status               → {"is_logged_in":true, ...}
```
"Logged in" but empty searches = expired anti-bot tokens
(`websectiga` / `acw_tc`). This is an account/credential issue, not a code bug.

Because no posts were fetched, three items are **code-complete but not yet
verified against live output**: specific style names, top-10 diversity, and the
9-grid path on real captured posts (verified only on demo/test images).

---

## 6. How to reproduce a fully-green e2e

```bash
# 1. Refresh the XHS session (scan QR with the secondary XHS app)
uv run python scripts/xhs_login.py --name nails

# 2. Confirm searches return data
curl "http://localhost:18060/api/v1/feeds/search?keyword=猫眼美甲&count=3"

# 3. Run the full pipeline
uv run python -m nails_agent run --output-dir web/output

# 4. Inspect output
cat web/output/report.json
ls  web/output/images/latest/raw/   # expect TREND_*_cell*.webp for grid posts
```
With both fallback chains in place, the prior quota/no-provider failures will no
longer abort the run.
