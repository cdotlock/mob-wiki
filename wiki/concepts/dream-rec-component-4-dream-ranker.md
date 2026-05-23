---
title: dream-rec Component 4 — Dream ranker design
updated: 2026-05-24
tags: [dream-rec, dream-ranker, component-4, recommendation]
sources: [docs/superpowers/specs/2026-05-23-dream-rec-component-4-dream-ranker-design.md]
status: shipped
---

# dream-rec Component 4 — Dream ranker

Upgrades `app/services/dream_ranker.py` from a popularity-only stub to an `axis_match × engagement × freshness` weighted scorer with continuous sharpness-driven blending into popularity. Resolves Component 0 §9 O5 (the weight coefficients).

See [[concepts/dream-rec-integration-architecture]] for Component 0 wiring.

## Decisions locked

- **Combination:** additive on `[0, 1]`: `total = α·axis_match + β·engagement + γ·freshness`, with `α + β + γ = 1`. Multiplicative rejected (zero freshness nukes good matches); RRF rejected (loses score-scale signal).
- **axis_match metric:** cosine similarity remapped to `[0, 1]`: `(cos(z_user, z_dream) + 1) / 2`. ε = 1e-9 in the cosine denominator. Inner product is biased toward high-|θ| users; weighted Euclidean has no natural upper bound.
- **engagement source:** read-only consume of `DreamSignature.engagement_stats` JSONB. Writes belong to [[concepts/dream-rec-component-6-dashboard]] / Loop C job, not the ranker.
- **engagement formula:** `clip(0.6·completionRate + 0.3·replayRate + 0.1·(1 − exitRate), 0, 1)`. Missing all keys → 0.5 neutral (not 0; avoids cold-start dream death spiral).
- **freshness:** `0.5 ^ (age_days / HALFLIFE_DAYS)`, default 45 days. Env override: `RANKER_FRESHNESS_HALFLIFE_DAYS`. `created_at` None → 0.5.
- **Default coefficients:** personalized `(α, β, γ) = (0.6, 0.3, 0.1)`; cold `(0.0, 0.7, 0.3)`. Env-overridable.
- **Sharpness blending (continuous, not binary):** `w_personal = clip((sharpness − τ_low) / (τ_high − τ_low), 0, 1)`, `τ_low = 0.3`, `τ_high = 0.7`. `axis_match_effective = w_personal · axis_match + (1 − w_personal) · engagement`. Existing `SHARPNESS_FALLBACK=0.5` retained for response-flag semantics but ranker internals always use the continuous formula.
- **Damaged signature handling:** `axis_position` missing `n_missing` keys → `damage_factor = max(0.3, 1.0 − 0.3·n_missing)` multiplier on `axis_match`. Doesn't break α + β + γ = 1.
- **`used_cold_start_matrix=true`:** additional 0.5 multiplier on `axis_match` (preserves normalization invariant rather than mutating α).
- **Candidate pre-filter:** SQL hard-constraint filter first, in-memory rank after. `RANKER_CANDIDATE_LIMIT = 500`.
- **Hard constraints (snake_case + camelCase compat):** read both naming conventions on `DreamSignature.hard_constraints` JSONB; new writes from [[concepts/dream-rec-component-2-llm-tagger]] are snake_case.
- **Failure modes:** missing θ / projection → cold coefficients (no 500); per-dream `axis_position` missing → damage_factor on that one item, not a global reject.

## Signature change

```python
# Stub:
def rank(db, novel_id, top_k, exclude_dream_ids, progress_at,
         required_flags, content_rating_max, used_fallback): ...

# Component 4:
def rank(db, *, novel_id, top_k, exclude_dream_ids, progress_at,
         required_flags, content_rating_max,
         user_id, theta_mean, theta_cov, sharpness, schema_version,
         used_fallback): ...
```

`app/routes/recommend.py` thread-throughs the new params.

## Response schema delta

Adds `user_theta_summary.used_cold_start_matrix: bool` (additive — no existing field touched). Drives ranker's cold-matrix branch and lets callers warn the UI.

## Test coverage (32 cases)

- axis_match: identity match (1.0), reversed (0.0), zero θ (0.5), damaged signatures
- sharpness blending: w_personal at sharpness 0.3/0.5/0.9
- engagement: full keys, empty dict (0.5), partial keys
- freshness: now (1.0), 45d (0.5), 90d (0.25), None (0.5)
- hard_constraints: snake_case + camelCase both reject correctly
- total_score: personalized + cold coefficients
- failure modes: UserGlobalTheta missing, GenreProjection missing, schema mismatch
- `reason` field: `"high_<axis>_match"`, `"popularity_fallback"`, `_cold_genre` suffix

Existing `test_recommend.py` (4 cases) stays green — cold-start response semantics preserved.

## Performance budget

- Ranker internals < 100ms (candidate fetch + score for ≤500 dreams)
- `GET /recommend` end-to-end < 200ms (Component 0 §5.2)
- ANN upgrade path noted for corpora >10k dreams (P2)

## What's deliberately NOT done

- Per-genre `(α, β, γ)`: P0 uses global coefficients; tune per-genre after P1 data drops.
- DB-backed `ranker_config` table: env vars only at P0.
- `score ± σ` uncertainty bands using θ_cov: interface left open, not consumed at P0.
- `engagement_stats` writer job — owned by [[concepts/dream-rec-component-6-dashboard]] Loop C.

## Cross-links

- [[concepts/dream-rec-integration-architecture]]
- [[concepts/dream-rec-component-1-tirt-estimator]] — provides θ_mean / sharpness
- [[concepts/dream-rec-component-3-genre-projection]] — provides z_user_genre + used_cold_start_matrix
- [[concepts/dream-rec-component-2-llm-tagger]] — provides axis_position + hard_constraints
