---
title: dream-rec integration architecture (Component 0)
updated: 2026-05-24
tags: [dream-rec, recommendation, moonshort-backend, architecture, component-0]
status: shipped
---

# dream-rec integration architecture (Component 0)

Independent Python FastAPI recommendation service that consumes choice events from `moonshort-backend` and returns ranked Dream sidequests for a (user, novel) pair. Built **alongside** the existing producer-side [[concepts/dream-trigger-v2-mechanical]] — they do not overlap: trigger v2 decides *when* a dream is triggered (1536-d UserNovelProfile.vector, deterministic); dream-rec decides *which* dream to recommend (5+1-axis Bayesian θ, personalized).

## Role

- **Producer service:** `moonshort-backend` (Next.js, port 3000) — writes choice events, owns the player-facing API.
- **Consumer service:** `dream-rec` (FastAPI, port 8766) — Python, separate process, separate Postgres schema (`dream_rec`), same database instance.
- **Communication:** HTTP only. dream-rec **never reads or writes** any `moonshort` table directly; cross-service data goes through `BackendClient.get_user_novel_profile / get_episode_source / get_dream` against `/api/internal/*` endpoints with bearer auth.
- **Coexistence with trigger v2:** trigger v2 stays unchanged. dream-rec runs in parallel; recommend results are surfaced to the player after trigger v2 elects to trigger a dream.

## Theoretical base

5 main personality axes (openness, sensation, cognition, affect, attachment) + 1 agency play-style axis. Bayesian Thurstonian IRT (TIRT) with heteropolar keying and testlet structure. See [[concepts/dream-rec-theoretical-base]] (companion spec, Bayesian TIRT). Sub-specs:

- **Component 1:** [[concepts/dream-rec-component-1-tirt-estimator]] — shipped 2026-05-24. Bayesian TIRT Laplace updater with `(user, story_id)` testlet and LLM-confidence-weighted ψ².
- **Component 2:** [[concepts/dream-rec-component-2-llm-tagger]] — shipped 2026-05-24. Batch episode-level tagger producing ItemTag + DreamSignature against the mob-ai gateway.
- **Component 3:** [[concepts/dream-rec-component-3-genre-projection]] — shipped 2026-05-24. Hybrid (manual seed + PCA refinement) `M_g` matrices with shadow-swap versioning and cold-start identity-on-5-core fallback.
- **Component 4:** [[concepts/dream-rec-component-4-dream-ranker]] — shipped 2026-05-24. `axis_match × engagement × freshness` ranker with continuous sharpness blending into popularity.
- **Component 5:** [[concepts/dream-rec-component-5-cold-start]] — shipped 2026-05-24. 5-item forced-choice onboarding questionnaire feeding informative `(μ₀, Σ₀)` via the same TIRT likelihood.
- **Component 6:** [[concepts/dream-rec-component-6-dashboard]] — deferred. Streamlit dashboard for the three calibration loops A/C/B; design locked, awaits `recommend_log` + moonshort funnel API.

Component 0 (this page) wires the seams so the sub-components can land without touching transport, schema, or moonshort-backend.

## Database schema (`dream_rec`)

Same Postgres instance as moonshort (local: `noval_demo` DB); logical isolation via dedicated schema.

Tables (DDL in `alembic/versions/0001_initial_schema.py`):

| Table | Purpose |
|---|---|
| `theta_schema_version` | versioned axis set (only one row `is_active=true`); referenced by all per-row `schema_version` columns |
| `user_global_theta` | per-user θ mean + cov + sharpness + choice_count |
| `choice_event` | outbox; idempotency_key UNIQUE; `process_status ∈ pending|processed|failed|skipped_no_tag` |
| `item_tag` | LLM-tagged loadings per choice option, with confidence; partial unique on `(novel, episode, choice_step, option, schema_version) WHERE superseded_by IS NULL` |
| `dream_signature` | LLM-inferred axis_position + hard_constraints per dream; partial unique on `(dream_id, schema_version) WHERE superseded_by IS NULL` |
| `scene_coverage_flag` | reports missing heteropolar coverage |
| `genre_projection` | per-genre projection matrix from main axes to genre micro-axis |
| `cold_start_item` / `cold_start_response` | C5 questionnaire (added in migration 0003) |

**Key invariants:**

- **No deletes.** Retag / re-review inserts a new row + sets `superseded_by` on the old. History chain is auditable.
- **Per-row `schema_version`** so a `theta_schema_version` bump doesn't invalidate historical rows.
- **`superseded_by` FK is DEFERRABLE INITIALLY DEFERRED** so insert + supersede can happen in one transaction without violating the partial unique index.

## API surface

All routes except `/health` require `Authorization: Bearer ${DREAM_REC_BEARER}`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/events/choice` | moonshort → dream-rec, fire-and-forget choice event (idempotent via `idempotency_key`) |
| POST | `/tag/novel` | enqueue LLM tagging of a novel's choices (background task) |
| POST | `/tag/dream` | enqueue LLM signature inference for a Dream (background task) |
| GET | `/recommend` | ranked Dream list; honors `content_rating_max`, `progress_at`, `required_flags`, `exclude_dream_ids`, `fallback_on_low_sharpness` |
| GET | `/theta/{user_id}` | introspect a user's persona state |
| GET | `/reviews/items` | list LLM-tagged items pending human review |
| POST | `/reviews/items/{id}` | approve / reject / edit a pending tag (supersede chain) |
| GET | `/reviews/dreams` | list pending Dream signatures |
| POST | `/reviews/dreams/{id}` | approve / reject / edit a pending Dream signature |
| GET | `/cold-start/items` | C5 questionnaire items (blind format — no scoring info exposed) |
| POST | `/cold-start/submit` | C5 submit + write informative prior |
| GET | `/health` | service status + outbox metrics (pending / failed counts) |

## Cold start + fallback

`is_cold_start` when `user is None or choice_count < 3`. `low_sharpness` when `sharpness is None or sharpness < SHARPNESS_FALLBACK`. When `(is_cold_start or low_sharpness) and fallback_on_low_sharpness`, ranker falls back to popularity (`engagement_stats.completionRate` desc) and reports `used_fallback=True` per item, `used_cold_start=True` in the summary.

## Outbox pattern

`/events/choice` writes a `choice_event` row inside the request, then calls `process_choice_event` synchronously inside the same transaction. If processing fails or no `item_tag` matches, the event is still durable in the table — the standalone `app/workers/outbox.py` worker picks up `pending|failed` events every 30s and retries. Idempotency key prevents duplicate inserts on retry from the client.

## moonshort-backend integration (PR open 2026-05-24)

Three hook points feeding events live in `moonshort-backend`, re-authored on 2026-05-24 against the current `origin/main` after the original cherry-pick conflicted with [[concepts/dream-trigger-v2-mechanical|Dream Trigger v2]]'s overlapping changes at the same call sites (see [[concepts/dream-rec-trigger-v2-coexistence]] for the coexistence design). Branch `feat/dream-rec-integration` pushed to `cdotlock/moonshort-backend`; **PR open at [#3](https://github.com/cdotlock/moonshort-backend/pull/3)** awaiting colleague review. Original worktree at `/tmp/msb-dream-rec` (ephemeral); patches archived in `dream-rec/docs/integration-patches/` as backup.

1. **`87360e66 feat(dream-rec): wire submitChoice to dream-rec service`** — adds `app/services/dream-rec-client.ts` (`postChoiceEvent / postTagNovel / postTagDream`), modifies `app/services/save-action-service.ts:submitChoice` to capture `action.id`, build `dreamRecPayload` inside the prisma tx, and fire `postChoiceEvent` after commit (side-by-side with v2's profile-vector update), and adds `DREAM_REC_URL / DREAM_REC_BEARER / DREAM_REC_ENABLED` to `.env.example`.
2. **`67ea73eb feat(dream-rec): trigger dream signature on dream finalize`** — `app/api/internal/dream-production-jobs/[jobId]/checkpoint/route.ts` fires `postTagDream` when `finalizedDream` exists, alongside v2's producer-snapshot block.
3. **`1a09a000 feat(dream-rec): trigger novel tagging after seed completes`** — `scripts/_seed-helpers/seed-runner.ts` fires `postTagNovel` at the end of `runSeed` so the LLM tagger ingests freshly-published episodes.

Helper: `app/services/dream-rec-client.ts` with `postChoiceEvent / postTagNovel / postTagDream` reading `DREAM_REC_URL / DREAM_REC_BEARER / DREAM_REC_ENABLED` env vars. All calls are fire-and-forget — moonshort never blocks on dream-rec. Default `DREAM_REC_ENABLED=false` — safe rollback flag.

## Status (2026-05-24)

Component 0 fully implemented; C1-C5 fully shipped; C6 deferred (design locked). Real-environment smoke verified against local Postgres on 2026-05-24:

- Cold-start → C1 Laplace MAP → 6-axis θ posterior with 6×6 covariance
- `/events/choice` → TIRT incremental update fires; θ moves monotonically with option loadings (5× option-a choices pushed all 6 axes in loading direction, sharpness 1.658 → 1.737)
- `/recommend` returns properly-ranked dreams (axis_match 0.93 → 0.05 across 6 seeded dreams; freshness 45-day half-life correctly tips ties when axis-match is close)

Test count: 367 pytest passing, ruff clean across `app/tests/scripts`.

**Path:** `~/MobAI/dream-rec` (FastAPI service)
**Plan:** `docs/superpowers/plans/2026-05-23-dream-rec-integration-architecture.md`
**Spec:** `docs/superpowers/specs/2026-05-23-dream-rec-integration-architecture-design.md`
**Theoretical spec:** `docs/superpowers/specs/2026-05-20-dream-rec-recommendation-design.md`
**Seed script (dev only):** `scripts/seed_dev_dreams.py`
