---
title: Dream Trigger v2 — Mechanical Evaluator (no LLM)
tags: [dreaming, trigger, embedding, vector, mechanical]
sources: [docs/superpowers/specs/2026-05-21-dream-trigger-mechanical.md]
created: 2026-05-21
updated: 2026-05-21
---

Mechanical (no-LLM) replacement for the producer-side gating logic inside `evaluateInPlayTrigger` / `evaluatePostPlayTrigger` in [[entities/lunaverse-backend]]. Lives under [[concepts/dreaming-universe]]; replaces the v1 single-gate of "committed_success ≥ 3 + phase dedup" with a multi-gate verdict driven by a per-(user, novel) preference vector, increment counters, and an input-sharpness self-check. Out of scope: public-pool matching, recommendation, the dream-agent itself — those are owned by a different stream and unaffected.

## Why mechanical

LLM-based judgment was prototyped first, but per-trigger LLM latency (~3-10s for a chain-of-thought verdict) was incompatible with the in_play fire-and-forget hook: any backpressure on remix-commit propagates to user-perceived response time. The mechanical evaluator runs in single-digit ms (one vector cosine, four counts, three sharpness aggregates) and burns at most one fire-and-forget embedding budget per remix/choice event (~150ms × 2 = ~300ms in background).

The core asset is `UserNovelProfile.vector(1536)` — one pgvector per (user, novel) accumulated by `remix + choice` events via a **weighted running mean**. At dream finalize time the vector is frozen into the `Dream.producerVector` snapshot column. Next evaluator pass computes `1 - cosine(current vector, lastDream.producerVector)` as the **drift** signal — the engine of "has the player evolved enough since the last dream to justify producing a new one?"

## Decisions

| Decision | Locked-in value |
|---|---|
| User dimension | (user, novel) — no per-LI split |
| Embedding write | Synchronous embedText fire-and-forget; never blocks the request transaction |
| Global centroid (distinctiveness) | Hardcoded null/zero — feature off in v2 |
| Public pool / recommendation | Out of scope, owned by colleague |
| First-dream eligibility | committed_success ≥ 3 → ready, no Stage 2/3 check |
| Dream count history | (user, novel) full history; not reset by saveSlot |
| Failure weighting | Achieved by per-event weights, NOT a Stage 2 override |
| Phase dedup | **Removed** — in_play / post_play each can fire repeatedly; drift + signals naturally rate-limit |

## Weight Table

Every event entering the running mean carries a weight `w`:

| Event | w | Meaning |
|---|---|---|
| Remix `committed_failed` | **2.0** | Active intervention + blocked. Strongest suppressed-intent signal |
| Remix `committed_success` | 1.0 | Active intervention + passed. Baseline |
| Brave choice fail (D20 fail) | 1.0 | Natural risk-taking + pain |
| Brave choice success | 0.6 | Natural risk-taking + success |
| Safe choice | 0.3 | Most passive signal; only contributes volume |

All weights tunable via the `WEIGHTS` constant in `app/services/dream-profile-vector.ts`.

## Embedding Composition — Dual-Vector Linear Combine

Context weight must be lower than action weight. Implementation: two `embedText` calls + linear combine.

```ts
const vAction  = await embedText(actionPrompt);    // ~150ms
const vContext = await embedText(contextPrompt);   // ~150ms
const final    = normalize(scale(vAction, 0.7) + scale(vContext, 0.3));
```

Both embeds run outside the request transaction, so the ~300ms total never blocks the commit response. Failures are caught and logged via `remix.commit.profile_embed_failed` / `submit_choice.profile_embed_failed`; the profile pauses accumulation and the next event re-arms it.

### Prompt templates

| Source | Template |
|---|---|
| Remix action | `The player intervened with a {attr} approach and {succeeded\|failed}: "{inputText}"` |
| Choice action | `Without intervening, the player chose the {brave\|safe} option and {succeeded\|failed\|just selected}: "{optionText}"` |
| Context (shared) | preceding 3 visible LS steps as plain text, one per line, capped at 400 chars |

Anchor context is extracted via the pure helper `app/core/anchor-context.ts:extractAnchorContext(episode, cursor, lookback)`. Walks the EpisodeJSON tree, keeps only renderable dialogue/narration/text_message steps, and truncates from the head so the most recent beats survive.

## Running Mean SQL

```sql
INSERT INTO "UserNovelProfile" (id, "userId", "novelId", vector, "totalWeight", "embCount", ...)
VALUES ($id, $userId, $novelId, $newVec::vector, $w, 1, ...)
ON CONFLICT ("userId", "novelId") DO UPDATE SET
  vector = CASE
    WHEN "UserNovelProfile".vector IS NULL THEN EXCLUDED.vector
    ELSE ("UserNovelProfile".vector * "UserNovelProfile"."totalWeight" + EXCLUDED.vector * $w)
       / ("UserNovelProfile"."totalWeight" + $w)
  END,
  "totalWeight" = "UserNovelProfile"."totalWeight" + $w,
  "embCount"    = "UserNovelProfile"."embCount" + 1,
  "updatedAt"   = NOW();
```

Cold start (vector IS NULL) goes through the insert branch; subsequent events fold into the weighted mean.

## Evaluator Flow

```text
evaluateDreamReady(userId, novelId, phase) → Verdict

Stage 0 — in-flight short-circuit
  hasInFlightAnyPhase → skip("production_in_flight")

Stage 1 — first-dream branch
  no lastDream && committed_success < 3 → skip("warming_up")
  no lastDream && committed_success ≥ 3 → ready("first_dream")

Stage 2 — signal increments since last snapshot
  profile.vector IS NULL → skip("profile_uninitialized")  // defensive
  drift = 1 - cosine(profile.vector, lastDream.producerVector)
  signals = (drift > τ) + (newCommits ≥ 2) + (newFails ≥ 1) + (newChoices ≥ 5) + affShifted
  effDreamCount = isLastDreamFinished(lastDream) ? dreamCount : dreamCount - 1
  τ        = [0.15, 0.25, 0.35][eff]   // 越往后越难 trigger
  needSig  = [1,    2,    2   ][eff]
  signals < needSig → skip("signals_X/Y_drift_Z")

Stage 3 — input sharpness
  medianLen < 12  → skip("input_too_short")
  lexDiv    < 0.35 → skip("input_too_repetitive")
  cohesion  < 0.55 → skip("cohesion_low_X")  // mean cosine of last-N committed remixes to centroid

ready("signals_and_sharpness_pass")
```

`evaluateInPlayTrigger` / `evaluatePostPlayTrigger` keep their phase-specific preconditions (session is Active for in_play, save is Completed for post_play), then delegate to `evaluateDreamReady`. The v1 commit-count gate, phase dedup, and prior-in_play guard on post_play are removed — drift + signal gating naturally rate-limits.

## Hooks (three sites)

| # | Site | Effect |
|---|---|---|
| A | `app/api/remix/commit/route.ts` after success | Extract anchor context, write to `Remix.anchorContext`, fire-and-forget `applyRemixToProfile` |
| B | `app/services/save-action-service.ts` submitChoice after ActionRecord.create | Embed anchorContext in ActionRecord.payload, fire-and-forget `applyChoiceToProfile` |
| C | Dream finalize (`app/api/internal/dream-production-jobs/[jobId]/checkpoint/route.ts`) | Snapshot UserNovelProfile + tallies into `Dream.producer*` columns after `runFinalizeTxn` |

All three hooks run outside the request transaction (Hooks A/B fire-and-forget, Hook C is a follow-up update). A failure in any never aborts the user-visible operation.

## Schema Delta

`UserNovelProfile` (dream-service DB):
- `embCount    Int   @default(0)` — raw event count (remix + choice combined)
- `totalWeight Float @default(0)` — denominator of the weighted running mean

`Dream` (dream-service DB) — all nullable; pre-2026-05-21 rows have no snapshot:
- `producerVector vector(1536)?`
- `producerTotalWeight Float?`
- `producerCommittedCount Int?`
- `producerFailedCount Int?`
- `producerChoiceCount Int?`
- `producerAffectionTop Json?` — top-3 character slug[]
- `producerSnapshotAt DateTime?`

`Remix` (main DB):
- `anchorContext String? @db.Text` — captured at commit time so the embed hook and offline replay don't refetch OSS

`ActionRecord.payload` (no schema change — JSON free-form):
- `anchorContext` added to `type: "choice-made"` payload

Migrations: `services/dream/prisma/migrations/20260521120000_dream_trigger_v2/` and `prisma/migrations/20260521120000_remix_anchor_context/`. All columns nullable or have defaults; rollback is `ALTER TABLE DROP COLUMN`.

## Tunables

Centralized at the top of `app/services/dream-profile-vector.ts`:

```ts
WEIGHTS = { remixFail: 2.0, remixSuccess: 1.0, braveFail: 1.0, braveSuccess: 0.6, safe: 0.3 }
ACTION_VECTOR_WEIGHT = 0.7
CONTEXT_VECTOR_WEIGHT = 0.3
CONTEXT_LOOKBACK_STEPS = 3
CONTEXT_CHAR_CAP = 400
DRIFT_TAU = [0.15, 0.25, 0.35]        // τ_0, τ_1, τ_2+
SIGNALS_NEEDED = [1, 2, 2]            // needSig_0, needSig_1, needSig_2+
NEW_COMMITS_FOR_SIGNAL = 2
NEW_FAILS_FOR_SIGNAL = 1
NEW_CHOICES_FOR_SIGNAL = 5
COHESION_FLOOR = 0.55
LEX_DIV_FLOOR = 0.35
MEDIAN_LEN_FLOOR = 12
FIRST_DREAM_COMMITTED_FLOOR = 3
```

Tune after one week of production data; single commit changes the dial.

## Files Touched

```
New:
  app/services/dream-profile-vector.ts                          (helper module + tunables)
  app/core/anchor-context.ts                                    (pure extractor)
  app/services/dream-trigger-service.legacy.ts                  (v1 rollback fallback, delete on/after 2026-05-28)
  services/dream/prisma/migrations/20260521120000_dream_trigger_v2/migration.sql
  prisma/migrations/20260521120000_remix_anchor_context/migration.sql
  scripts/dream-trigger-mechanical-smoke.ts                     (standalone smoke; pnpm smoke:dream-trigger-mechanical)
  __tests__/core/anchor-context.test.ts                         (8 cases)
  __tests__/services/dream-profile-vector.test.ts               (24 cases)
  __tests__/services/dream-trigger-service.evaluate-mechanical.test.ts (10 cases — one per skip reason + both ready branches)

Modified:
  prisma/schema.prisma                                          (Remix +anchorContext)
  services/dream/prisma/schema.prisma                           (UserNovelProfile + Dream columns)
  app/services/dream-trigger-service.ts                         (evaluateDreamReady + delegating evaluate*)
  app/api/remix/commit/route.ts                                 (Hook A)
  app/services/save-action-service.ts                           (Hook B)
  app/api/internal/dream-production-jobs/[jobId]/checkpoint/route.ts (Hook C)
```

## Risks + Rollback

| Risk | Mitigation |
|---|---|
| Embedding service down | Write path try/catches per-event, profile pauses accumulation; evaluator treats `profile.vector IS NULL` as "warming_up" so the system fails open to first-dream behavior |
| Threshold mis-tuning | All magic numbers in one file; single commit re-tunes |
| Full rollback needed | `dream-trigger-service.legacy.ts` retains the v1 body for 1 week; swap import + delete after 2026-05-28 |
| Migration rollback | All new columns nullable or have defaults; safe `ALTER TABLE DROP COLUMN` |

## Out of Scope (explicit)

- Public-pool matching / dream adapter agent
- Distinctiveness term (global centroid hardcoded null)
- per-LI dimension
- characterBible refactor / storyline tag (2026-05-24 status: characterBible refactor landed — renamed to `characterArcs` + extracted to `NovelDreamArtifact` 1:1 sidecar; see [[concepts/novel-dream-artifact]])
- in_play / post_play trigger timing itself (still remix-commit fire-and-forget + Completed + 8h delay)
- Online threshold tuning / admin panel

## Related

- [[concepts/dreaming-universe]] — umbrella product + technical model
- [[concepts/remix-anywhere]] — upstream event source feeding the profile vector
- [[concepts/stable-step-id]] — anchor cursor format used by `extractAnchorContext`
