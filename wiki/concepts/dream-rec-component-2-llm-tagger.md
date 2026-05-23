---
title: dream-rec Component 2 — LLM tagger design
updated: 2026-05-23
tags: [dream-rec, llm-tagger, component-2, recommendation]
sources: [docs/superpowers/specs/2026-05-23-dream-rec-component-2-llm-tagger-design.md]
---

# dream-rec Component 2 — LLM tagger design

Replaces the 12-line stub at `app/services/llm_tagger.py` with a batch, offline tagger that produces (a) `ItemTag` loadings per `@choice` option on the 6-axis schema and (b) `DreamSignature` axis_position + hard_constraints + confidence per Dream.

See [[concepts/dream-rec-integration-architecture]] for Component 0 wiring. See [[concepts/stable-step-id]] for why we parse compiled JSON not source MSS.

## Decisions locked

- **Provider:** mob-ai gateway (`https://ai.mob-ai.cn/v1`), OpenAI-compatible. Same gateway as [[entities/assets-produce]].
- **Model:** `mob-ai/claude-sonnet-4-7`.
- **Granularity:** Episode-level batch — one LLM call per episode, prompt contains all choices + their option texts + branch summaries.
- **Confidence:** Self-reported by model; `confidence >= TAU_REVIEW=0.7` → `auto_accepted`, below → `pending_review`.
- **Execution:** FastAPI `BackgroundTasks` + resumable tagger (skip-already-tagged via partial unique index lookup). No new outbox table.
- **Parser:** `compiled_walker.py` walks compiled JSON (stable step ids baked in by MSS compiler), not source MSS markdown regex.
- **Concurrency:** `LLM_MAX_CONCURRENCY=4` semaphore across episodes within a single novel tagging job.
- **Retry:** `LLM_RETRY_MAX=1`. On second failure → that episode's options → `pending_review` with `confidence=0`, loadings all zero, structured log.
- **scene_coverage_flag:** Emitted per (axis × choice_step) when all option loadings on that axis are same-signed and exceed `±0.3`. Loop A diagnostics consume these.
- **Idempotency:** `force_retag=false` skips already-tagged options for active schema_version; `force_retag=true` walks supersede chain (pre-generated UUID + DEFERRABLE FK from Task 10).

## Package layout

```
app/services/llm_tagger/
├── __init__.py        exports tag_novel, tag_dream
├── client.py          OpenAI client (mob-ai gateway)
├── schema.py          Pydantic IO schemas
├── prompt.py          Prompt templates
├── compiled_walker.py choice extraction from compiledJson
├── novel_tagger.py    per-episode driver
├── dream_tagger.py    per-dream driver
└── coverage.py        heteropolar checker
```

## BackendClient methods required

- `get_novel_episodes_list(novel_id)` — **NEW**, hits `/api/internal/novels/{novelId}/episodes`
- `get_episode_source(novel_id, episode_id)` — already exists (Task 13), returns `{compiledJson, ...}`
- `get_dream(dream_id)` — already exists (Task 13), contract returns `{title, summary, genre, first_episode_compiled, hard_constraint_hints?}`

## What's deliberately NOT done

- Real LLM end-to-end tests (cost + flakiness). Mocked in CI, manual smoke separate.
- Multi-provider abstraction (YAGNI; mob-ai is the chosen path).
- Prompt response caching (mob-ai's ephemeral cache doesn't propagate through the gateway).
- Cross-episode context (one episode per LLM batch is enough).
- Component 3+4 dependencies — when GenreProjection isn't yet populated for a genre, fall back to identity projection.

## Status

Design spec approved 2026-05-23. Implementation plan (via `superpowers:writing-plans`) and execution (via `superpowers:subagent-driven-development`) pending.

**Spec file:** `~/MobAI/dream-rec/docs/superpowers/specs/2026-05-23-dream-rec-component-2-llm-tagger-design.md`
**Repo:** [AugustZAD/dream-rec](https://github.com/AugustZAD/dream-rec), branch `main`, commit `88456c2`.
