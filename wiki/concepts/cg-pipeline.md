---
title: CG Pipeline (07.5 step)
tags: [novels-to-moonscript, asset-pipeline, cg, mss]
last_verified: 2026-05-13
---

# CG Pipeline (07.5 step)

Three-layer pipeline that turns `@cg show <name>` MSS directives into rendered static images (Phase 1 single-panel + Phase 2 manga multi-panel) and surfaces URLs into `mapping.json`. Phase 3 (AI video gen) is config-gated and deferred to agent-forge.

## Layers

- **Layer A** — `skills/asset-prompt-generator/cg_collector.py` + `llm_shot_splitter.py` (novels-to-moonscript)
  - Scans `*.mss.md` for `@cg show <name> { duration: ... content: "..." ... }` blocks
  - Calls LLM (anthropic Sonnet by default) to split content prose into ordered keyframe panels (cap by duration tier: low=1, medium=2, high=4)
  - Emits `tasks_output.json.cg_tasks[]`
  - Fallback: single-panel on any LLM failure (renderer never stalls)

- **Layer B** — `moonshort-backend/generate-upscale-matting/cg_render.py`
  - Consumes `cg_tasks[]`, calls existing `render-with-style.py` helpers via `importlib` (filename has hyphen)
  - Outputs `assets/<slug>/cg/<name>.webp` then uploads to `nrbi/cg/<name>.webp` on OSS
  - `render_mode == "video"` raises `NotImplementedError` (P3 placeholder)

- **Layer C** — `dramatizer/pipeline/cg_{config,stage,mapping,oss_list}.py` (novels-to-moonscript)
  - `cg_config.py`: parses yaml `cg:` section
  - `stage_cg.py`: hardlinks local cg/*.{webp,mp4} into `dramatizer/assets/<slug>/cg/`
  - `cg_oss_list.py`: lists OSS keys under `nrbi/cg/` prefix
  - `cg_mapping.py`: builds flat `{cg_name: url}` dict
  - Wired into `dramatizer/build.py` at Step 1.7 (stage) + Step 2.4 (mapping merge)

## Engine contract (frozen)

- `mapping.json[cg_name]` value is always `string` — never array, never object. P1/P2/P3 all serialize as 1 URL per CG.
- File extension dispatch is frontend-only: `.webp` → `<img>`, `.mp4` → `<video autoplay loop muted playsinline>`.
- MSS Go interpreter zero-changes — `cg_show` step already has `url` field bake-in.
- body NARRATOR / YOU under `@cg show { ... }` remain click-through per canonical spec.

## Phase split

| Phase | Format | When |
|---|---|---|
| **P1** | 1 webp single-panel | content prose has 1 shot (no "cut to" / "pull back") |
| **P2** | 1 webp N-panel manga grid | content prose has ≥2 shots |
| **P3** | 1 mp4 AI video | deferred to agent-forge; enable via `cg.video_renderer.enabled` |

## NRBI status (2026-05-13)

- 4 finale CGs in `ep_22_weston_awakening_final.md` are seeded into `tasks_output.cg_tasks[]` with hand-curated panel splits (LLM splitter substitute when ANTHROPIC_API_KEY is empty).
- MCP `style-prompts` has `cg_single_panel_style` and `cg_manga_panel_style` upserted under `korean-manga-style` style, category=`scene` (server enum constraint).
- Reference images: reuse `scene/location_style.png` (single) + `scene/location_grid_style.png` (multi-panel) — both verified live on OSS.
- Actual rendering of the 4 CGs is **blocked on a working `ZENMUX_API_KEY`** with nano-banana-pro permission (current key returns 403).

## Files

- Spec: [`novels-to-moonscript/docs/superpowers/specs/2026-05-13-cg-pipeline-design.md`](https://github.com/AugustZAD/novels-to-moonscript/blob/main/docs/superpowers/specs/2026-05-13-cg-pipeline-design.md)
- Plan: [`novels-to-moonscript/docs/superpowers/plans/2026-05-13-cg-pipeline-impl.md`](https://github.com/AugustZAD/novels-to-moonscript/blob/main/docs/superpowers/plans/2026-05-13-cg-pipeline-impl.md)

## Tests at landing

- Layer A: 25 tests in `skills/asset-prompt-generator/tests/test_cg_collector.py` + `test_llm_shot_splitter.py` (1 skipped — live anthropic smoke)
- Layer B: 18 tests in `moonshort-backend/generate-upscale-matting/tests/test_cg_render.py`
- Layer C: 14 tests across `test_cg_config.py`, `test_cg_oss_list.py`, `test_cg_mapping.py`, `test_stage_cg.py`, + 1 added to `test_build_cli.py` (cg-section-without-OSS-creds case)
