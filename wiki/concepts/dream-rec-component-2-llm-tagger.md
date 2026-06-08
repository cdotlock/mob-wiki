---
title: dream-rec Component 2 — LLM-as-annotator tagger
updated: 2026-05-24
tags: [dream-rec, llm-tagger, component-2, recommendation]
sources: [docs/superpowers/specs/2026-05-23-dream-rec-component-2-llm-tagger-design.md]
status: shipped
---

# dream-rec Component 2 — LLM-as-annotator tagger

Replaces the 12-line stub at `app/services/llm_tagger.py` with a batch, offline tagger that produces (a) `ItemTag` loadings per `@choice` option on the 6-axis schema and (b) `DreamSignature` axis_position + hard_constraints + confidence per Dream.

See [[concepts/dream-rec-integration-architecture]] for Component 0 wiring. See [[concepts/stable-step-id]] for why we parse compiled JSON not source LS.

## 6-axis schema

| Axis | Source | Polarity (+) | Polarity (−) |
|---|---|---|---|
| openness | BFI openness | Novel/abstract/aesthetic | Conservative/concrete/pragmatic |
| sensation | BSSS | Thrill/adventure/strong stimulation | Calm/safe/low-arousal |
| cognition | NCS | Deep reasoning/analysis | Intuitive/simplification |
| affect | PANAS | Positive expression/embracing emotion | Suppression/restraint |
| attachment | ECR-R | Trust/closeness | Avoidant/distant |
| agency | play-style | Active intervention | Passive observation |

Loadings ∈ [−1, +1]; strong correlation ±0.7~±1.0; neutral 0.

## Decisions locked

- **Provider:** mob-ai gateway (`https://ai.mob-ai.cn/v1`), OpenAI-compatible. Same gateway as [[entities/assets-produce]].
- **Model:** `mob-ai/claude-sonnet-4-6` (default env-overridable; `claude-sonnet-4-7` not routable on the gateway as of 2026-05-23).
- **Granularity:** Episode-level batch — one LLM call per episode, prompt contains all choices + their option texts + branch summaries.
- **Confidence:** Self-reported by model; `confidence >= TAU_REVIEW` → `auto_accepted`, below → `pending_review` (both pass downstream — review is for audit, not blocking). Default `TAU_REVIEW=0.0` (review disabled) as of 2026-05-24 per product decision; bump above 0 to re-enable human review for low-confidence tags.
- **Execution:** FastAPI `BackgroundTasks` + resumable tagger (skip-already-tagged via partial unique index lookup). No new outbox table.
- **Parser:** `compiled_walker.py` walks compiled JSON (stable step ids baked in by LS compiler), not source LS markdown regex.
- **Concurrency:** `LLM_MAX_CONCURRENCY=4` semaphore across episodes within a single novel tagging job.
- **Retry:** `LLM_RETRY_MAX=1`. On second failure → that episode's options → `pending_review` with `confidence=0`, loadings all zero, structured log.
- **Temperature 0.0** — deterministic for reproducible reviewer audits.
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

## Data flow

### tag_novel(novel_id, force_retag=False)

```
1. active_schema = SELECT version FROM theta_schema_version WHERE is_active
2. {episodes} = await backend.get_novel_episodes_list(novel_id)
3. async with Semaphore(LLM_MAX_CONCURRENCY):
     for episode in episodes:
       await tag_episode(novel_id, episode.episodeId, active_schema, force_retag)
4. structlog: {novel_id, episodes_total, episodes_tagged, options_total,
               options_pending, coverage_flags}
```

Per-episode driver: pull existing tags → fetch compiled JSON → walk choices → build prompt → LLM call → validate response → insert/supersede ItemTag rows → upsert SceneCoverageFlag rows → commit.

### tag_dream(dream_id, force_retag=False)

```
1. dream = await backend.get_dream(dream_id)
2. active_schema = active ThetaSchemaVersion.version
3. existing = SELECT dream_signature WHERE dream_id=D AND schema_version=v
              AND superseded_by IS NULL
4. skip if existing and !force_retag
5. projection = SELECT genre_projection WHERE genre=dream.genre AND is_active
   (fall back to identity 6-axis if no projection — see C3)
6. excerpt = compiled_walker.flatten_to_text(dream.first_episode_compiled,
                                              max_chars=4000)
7. raw = await llm_client.complete(build_prompt_for_dream(...))
8. signature = DreamSignatureResponse.model_validate_json(raw)
9. INSERT or supersede; status by TAU_REVIEW
10. COMMIT
```

## BackendClient methods required

- `get_novel_episodes_list(novel_id)` — hits `/api/internal/novels/{novelId}/episodes`
- `get_episode_source(novel_id, episode_id)` — returns `{compiledJson, ...}`
- `get_dream(dream_id)` — contract returns `{title, summary, genre, first_episode_compiled, hard_constraint_hints?}`

## Pydantic IO schemas

```python
class AxisLoadings(BaseModel):
    openness: float = Field(ge=-1.0, le=1.0)
    sensation: float = Field(ge=-1.0, le=1.0)
    cognition: float = Field(ge=-1.0, le=1.0)
    affect: float = Field(ge=-1.0, le=1.0)
    attachment: float = Field(ge=-1.0, le=1.0)
    agency: float = Field(ge=-1.0, le=1.0)

class ItemTagging(BaseModel):
    choice_step_id: str
    option_id: str
    loadings: AxisLoadings
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None  # debug/audit; not stored

class HardConstraintHints(BaseModel):
    progress_gate: int | None = None
    content_rating: Literal["General", "Mature", "Explicit"] | None = None
    flags_required: dict[str, str] = Field(default_factory=dict)

class DreamSignatureResponse(BaseModel):
    axis_position: dict[str, float]
    hard_constraints: HardConstraintHints
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None
```

## What's deliberately NOT done

- Real LLM end-to-end tests (cost + flakiness). Mocked in CI, manual smoke separate.
- Multi-provider abstraction (YAGNI; mob-ai is the chosen path).
- Prompt response caching (mob-ai's ephemeral cache doesn't propagate through the gateway).
- Cross-episode context (one episode per LLM batch is enough).
- Component 3+4 dependencies — when GenreProjection isn't yet populated for a genre, fall back to identity projection.

## Status (2026-05-24)

- Package shipped at `app/services/llm_tagger/` (11 sub-tasks, all green).
- Mocked end-to-end test covers `tag_novel` + `tag_dream` flow including supersede chain.
- Real LLM end-to-end not run (cost + flakiness — manual when reviewers want to dogfood).
- `/tag/novel` + `/tag/dream` routes wired in `app/routes/tag.py` with `BackgroundTasks` deferral.

**Spec file:** `~/MobAI/dream-rec/docs/superpowers/specs/2026-05-23-dream-rec-component-2-llm-tagger-design.md`
**Implementation plan:** `docs/superpowers/plans/2026-05-23-dream-rec-component-2-llm-tagger.md`
**Repo:** [AugustZAD/dream-rec](https://github.com/AugustZAD/dream-rec)
