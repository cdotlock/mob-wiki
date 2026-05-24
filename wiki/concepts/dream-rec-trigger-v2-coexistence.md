---
title: Dream Trigger v2 ↔ dream-rec Coexistence
created: 2026-05-24
updated: 2026-05-24
tags: [dream-rec, dream-trigger, moonshort-backend, integration, coexistence]
sources: []
status: shipped-integration-not-pushed
---

# Dream Trigger v2 ↔ dream-rec Coexistence

[[concepts/dream-trigger-v2-mechanical]] (TypeScript, in-process in `moonshort-backend`) and [[concepts/dream-rec-integration-architecture]] (Python FastAPI, separate service) were developed in parallel and merged into the same hook sites in [[entities/moonshort-backend]] between 2026-05-21 and 2026-05-24. Initial concern was duplication of work at the integration points (`submitChoice`, dream finalize, seed end). After a three-subagent investigation we concluded the two systems solve **different problems** and should coexist side-by-side, with one specific shared asset (`UserNovelProfile.vector` consumed as a ranker feature) and one shared input (the step-type taxonomy). This page records the scope split, the asset-by-asset decision matrix, and the current implementation status so the next person to touch either side does not re-litigate the design.

## System scope

**Dream Trigger v2 owns dream-timing** — the *when*. Decides whether to fire `evaluateInPlayTrigger` / `evaluatePostPlayTrigger` based on a 256-dim Jina embedding maintained per `(user, novel)` as `UserNovelProfile.vector`. The vector is updated by a weighted running mean over choice/remix anchor embeddings (weights `remixFail=2.0`, `remixSuccess=1.0`, `braveFail=1.0`, `braveSuccess=0.6`, `safe=0.3`) via `app/services/dream-profile-vector.ts`, and the mechanical evaluator gates on `drift = 1 - cos(vector, lastDream.producerVector)`, increment counters, and input sharpness. No LLM in the hot path. See [[concepts/dream-trigger-v2-mechanical]] for the full spec.

**dream-rec owns content-ranking** — the *which*. Once trigger v2 has elected to produce a dream (or once a recommendation list is requested), dream-rec returns a ranked Dream list for `(user, novel)`. Uses Bayesian Thurstonian IRT (Laplace approximation) to maintain a 6-axis θ vector in `user_global_theta`, fed by LLM-tagged option loadings stored in `item_tag` (`app/services/llm_tagger.py` produces these against the mob-ai gateway). Ranking score is `axis_match × engagement × freshness` with continuous sharpness blending into popularity fallback. See [[concepts/dream-rec-integration-architecture]] (C0 architecture) and the per-component specs: [[concepts/dream-rec-component-1-tirt-estimator]] (C1 estimator), [[concepts/dream-rec-component-2-llm-tagger]] (C2 tagger), [[concepts/dream-rec-component-4-dream-ranker]] (C4 ranker).

The two systems never write the same row. v2 writes `UserNovelProfile` + `Dream.producer*` snapshots in the dream-service Postgres schema. dream-rec writes `choice_event`, `user_global_theta`, `item_tag`, `dream_signature` in the `dream_rec` Postgres schema (same instance, separate logical schema, no cross-schema reads). The single integration is the hook sites in `moonshort-backend`: both consumers fire fire-and-forget calls after the same transaction commits, sharing `ActionRecord.id` as the natural idempotency key.

## Decision matrix

| Asset | Decision | Rationale |
|---|---|---|
| Hook points (`submitChoice`, dream finalize, seed end) | **Both fire side-by-side** | Different consumers, both need the same events. v2 already wired; dream-rec adds parallel fire-and-forget calls at the same call sites. `action.id` shared as idempotency key. |
| Anchor context extraction | **NO REUSE** | v2: anchor-relative 400-char window for embedding (`app/core/anchor-context.ts:extractAnchorContext`). dream-rec: episode-global ~4000-char window with structured choice list for LLM tagging (`app/services/llm_tagger.py`, walks compiled JSON). Different shapes, different consumers. |
| Step-type taxonomy markdown | **YES — single source** | Both consumers reference the same step-type taxonomy. One copy, both sides import. |
| `UserNovelProfile.vector` (256-dim Jina) | **YES — dream-rec reads as ranker feature** | dream-rec ranker can concatenate v2's 256-dim vector with the 6-axis θ when computing the final ranking score. NOT folded into the Laplace prior — θ remains the primary signal; the vector is an additive feature. |
| Event weight table (`remixFail=2.0`, etc.) | **DEFER** | Requires extending `ChoiceEvent` with `mode` (remix vs choice) and `outcome` (success/fail) fields. Schema change deferred until weights matter to dream-rec ranking. |
| θ → v2 evaluator (cold-start fallback) | **EXPERIMENTAL** | Low priority. Could use dream-rec θ sharpness as a fallback gate for v2 when `UserNovelProfile.vector IS NULL`, but the existing `warming_up` skip is sufficient. |

## Implementation status (2026-05-24)

Three dream-rec backend integration commits authored in worktree `/tmp/msb-dream-rec` on branch `feat/dream-rec-integration` (re-authored against current `origin/main` — the original cherry-pick had failed due to v2's context shifts):

| SHA | Title | Files | Diff |
|---|---|---|---|
| `87360e66` | feat(dream-rec): wire submitChoice to dream-rec service | 3 | +102/-1 |
| `1a09a000` | feat(dream-rec): trigger novel tagging after seed completes | 1 | +6 |
| `67ea73eb` | feat(dream-rec): trigger dream signature on dream finalize | 1 | +8 |

Commit 1 adds `app/services/dream-rec-client.ts` (`postChoiceEvent` / `postTagNovel` / `postTagDream`), modifies `app/services/save-action-service.ts` (capture `action.id`, build `dreamRecPayload` inside the tx, `postChoiceEvent` after commit), and adds `DREAM_REC_URL` / `DREAM_REC_BEARER` / `DREAM_REC_ENABLED` to `.env.example`. Commit 2 adds a `postTagNovel` call at the end of `runSeed` in `scripts/_seed-helpers/seed-runner.ts`. Commit 3 adds a `postTagDream` call when `finalizedDream` exists in `app/api/internal/dream-production-jobs/[jobId]/checkpoint/route.ts`.

All three commits coexist with v2's hooks at the same call sites — v2 and dream-rec each get their own fire-and-forget call after the same transaction commits, sharing `action.id` as the idempotency key.

**Not yet pushed.** `cdotlock/moonshort-backend` is a non-user namespace; per the global push rule the push needs explicit user authorization. Commits live in the worktree until then.

## Open questions

- **Event weight surface** — should `ChoiceEvent.mode` / `outcome` be added to dream-rec's outbox schema so the v2 weight table can influence ranker score? Currently `choice_event` does not distinguish remix-commit from regular choice. Re-evaluate after one week of production data.
- **θ → v2 evaluator cold-start fallback** — when `UserNovelProfile.vector IS NULL`, could dream-rec's θ sharpness substitute as a coarse readiness gate? Experimental, low priority. Need to confirm v2's `warming_up` skip rate before investing.
- **Cross-service DB access for vector read** — dream-rec currently has no read path to `UserNovelProfile`. If the ranker is to consume the 256-dim vector, options: (a) HTTP via `BackendClient.get_user_novel_profile` (already exists; would need to expose the vector); (b) direct cross-schema SQL (rejected by C0 — `dream-rec never reads or writes moonshort tables directly`). Decision deferred until the ranker actually needs the vector signal.

## References

- Staged commits worktree: `/tmp/msb-dream-rec` (branch `feat/dream-rec-integration`)
- dream-rec service: `/Users/august/MobAI/dream-rec`
- v2 helper: `app/services/dream-profile-vector.ts` in [[entities/moonshort-backend]]
- v2 anchor extractor: `app/core/anchor-context.ts`
- dream-rec LLM tagger: `app/services/llm_tagger.py`
- dream-rec client (TS side): `app/services/dream-rec-client.ts`
- Hook sites: `app/services/save-action-service.ts` (submitChoice), `scripts/_seed-helpers/seed-runner.ts` (seed end), `app/api/internal/dream-production-jobs/[jobId]/checkpoint/route.ts` (dream finalize)

## Related

- [[concepts/dream-trigger-v2-mechanical]] — v2 timing evaluator spec
- [[concepts/dream-rec-integration-architecture]] — dream-rec C0 service architecture
- [[concepts/dream-rec-component-1-tirt-estimator]] — θ posterior consumer
- [[concepts/dream-rec-component-2-llm-tagger]] — episode-global tagger that owns its own anchor extraction
- [[concepts/dreaming-universe]] — product umbrella
