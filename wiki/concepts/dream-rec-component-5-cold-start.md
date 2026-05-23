---
title: dream-rec Component 5 — Cold-start questionnaire design
updated: 2026-05-24
tags: [dream-rec, cold-start, component-5, recommendation]
sources: [docs/superpowers/specs/2026-05-23-dream-rec-component-5-cold-start-design.md]
status: shipped
---

# dream-rec Component 5 — Cold-start questionnaire

5-item forced-choice questionnaire shown during moonshort onboarding. Generates an informative `(μ₀, Σ₀)` prior on the new user's θ via the same Thurstonian likelihood [[concepts/dream-rec-component-1-tirt-estimator]] uses for live `ChoiceEvent` updates, then writes it as the seed `UserGlobalTheta` row.

See [[concepts/dream-rec-integration-architecture]] for Component 0 wiring.

## Decisions locked

- **Question count N = 5.** Lower bound from axis coverage (5+1 axes need ~5 items at 1.5 axis/item to identify all dims). Upper bound from onboarding funnel friction. Heister et al. 2025 shows TIRT info-gain elbow ≈ 5 items.
- **Item type: binary forced-choice (block size 2).** Same likelihood as live `@choice`, closed-form single-variable probit, 100% inference code path reused. Likert (graded response) and rank-order rejected — they introduce new likelihood families for marginal info-gain.
- **Multi-axis loadings per item.** Each option has K=6 loading vector (2–3 nonzero axes typical), so 5 items × multi-axis = rank-5 differential constraint matrix in 6-d θ, well-posed with `N(0, I_6)` prior.
- **Storage: independent `cold_start_response` table.** Not written to `choice_event`. Lifecycle differs (one-shot batch, no outbox/retry); source differs (curated items, no novel/episode/story); idempotency differs (`UNIQUE(user_id, item_id)` not `(user, session, step)`).
- **Inference: batch Laplace from `N(0, I_6)`**, reusing [[concepts/dream-rec-component-1-tirt-estimator]] §4.2 single-block Newton-Raphson sequentially across 5 items (mathematically equivalent to joint multi-block MAP).
- **Skip = no row.** Partial / abandoned wizard → no `cold_start_response` write, no `user_global_theta` write. First live `ChoiceEvent` triggers Component 1's `N(0, I_6)` seed.
- **Versioning:** `cold_start_item` rows reference `theta_schema_version`. Schema bump → new item set; old responses replayable for prior recompute.
- **Attention check:** schema slot `is_attention_check: bool` reserved; P0 unused. Enable in P1 if spam > 5%.
- **`confidence` field:** all P0 cold-start options forced to 1.0 (curated by hand, not LLM-tagged). Goes through the same `ψ²` mapping as live items.

## Schema additions (Alembic migration in implementation plan)

```
dream_rec.cold_start_item
├── id              uuid PK
├── schema_version  text FK → theta_schema_version
├── display_order   int           (1..N, UNIQUE per schema_version)
├── question_text   text
├── options         jsonb         # [{option_id, text, loadings, confidence}]
├── is_attention_check bool
├── is_active       bool
├── superseded_by   uuid (self-FK)
└── created_at      timestamptz

dream_rec.cold_start_response
├── id                  uuid PK
├── user_id             text
├── item_id             uuid FK → cold_start_item
├── selected_option_id  text         # 'a' | 'b'
├── schema_version      text FK
├── answered_at         timestamptz
└── UNIQUE (user_id, item_id)
```

## API surface (Component 0 §4 style)

```
GET  /cold-start/items?schema_version=v1.0.0
→ 200 { schema_version, items: [{item_id, display_order, question_text, options}] }
       (loadings stripped before serialization — preserves blind-test integrity)

POST /cold-start/submit
{ user_id, schema_version, responses: [{item_id, selected_option_id} × 5], client_meta? }
→ 200 { user_id, cold_start_done: true, theta_mean, sharpness, schema_version }
→ 400 if N ≠ 5 or invalid item_id / option_id
→ 409 if cold_start_done already true
```

Sync (not fire-and-forget) — moonshort onboarding completion page waits for the prior to be written.

## P0 question set (5 items, hand-curated)

Question topics cover the 6 axes with heteropolar coverage verified (each axis has both + and − polarity options across the set):

1. Weekend night preference (openness × sensation × cognition)
2. What draws you to a story (cognition × affect × sensation)
3. Intimate-relationship priorities (attachment × affect × agency)
4. Open-ended story endings (openness × cognition × agency)
5. Emotional resolution preferences (sensation × affect × attachment)

Item 6 (game agency) reserved as the R7 rotation pool starter.

## Failure modes

| Trigger | Action |
|---|---|
| Partial answers, user exits wizard | No DB write; live ChoiceEvent later seeds from `N(0, I_6)` |
| Extreme answers (all-a or all-b) | clip handles `|θ| → 4`; sharpness ≈ 2; not a fault |
| Network retry of `/cold-start/submit` | `UNIQUE(user_id, item_id)` blocks dup; if `cold_start_done=true`, 409 + current prior |
| `selected_option_id` not in `options` | 400 + `invalid_option_id`; no row written |
| Laplace numerical instability | Ridge `H + 1e-3·I` retry; warning; prior still written |
| `schema_version` mismatch on submit | 400; moonshort restarts wizard with active schema |

## Loop A / R7 hooks

- `cold_start_item.superseded_by` + `is_active` let Component 7 swap items while keeping replay-ability.
- `cold_start_response` is the BRM novelty data source: replay all 5 answers + subsequent `ChoiceEvent` chain for `θ_questionnaire` vs evaluation-battery (BFI-2-S, BSSS-8, NCS-6, NAQ-S, ECR-R, Raven's APM-12) correlation studies.

## What's deliberately NOT done

- Adaptive item selection (CAT): N=5 is small enough that fixed order is fine.
- `cold_start_done=false` rows with partial answers: skipped path uses absence-of-row, not row + flag.
- Locale / i18n: handled in moonshort UI.
- User migration on schema upgrade: covered in Loop C / Component 8 backlog.

## Cross-links

- [[concepts/dream-rec-integration-architecture]]
- [[concepts/dream-rec-component-1-tirt-estimator]] — likelihood reused; cold prior is just its first 5 updates
- [[concepts/dream-rec-component-2-llm-tagger]] — axes / confidence semantics borrowed for the curated item loadings
