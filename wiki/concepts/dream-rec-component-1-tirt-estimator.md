---
title: dream-rec Component 1 — Bayesian TIRT estimator design
updated: 2026-05-24
tags: [dream-rec, tirt-estimator, component-1, recommendation]
sources: [docs/superpowers/specs/2026-05-23-dream-rec-component-1-tirt-estimator-design.md]
status: shipped
---

# dream-rec Component 1 — Bayesian TIRT estimator

Replaces the choice-count stub at `app/services/tirt_estimator.py` with a per-event Bayesian Thurstonian IRT updater: each processed `ChoiceEvent` shifts the user's 5+1-axis posterior `(theta_mean, theta_cov)` using Laplace approximation around the joint MAP of θ and the `(user, story_id)` testlet random effect.

See [[concepts/dream-rec-integration-architecture]] for Component 0 wiring. Consumes `ItemTag.loadings` + `confidence` from [[concepts/dream-rec-component-2-llm-tagger]].

## Decisions locked

- **Online update algorithm:** Laplace approximation around posterior mode. Newton-Raphson MAP, Hessian inverse as posterior cov. (VI and particle filter rejected: 6+1 dims are too small to justify ELBO overhead or particle sparsity; probit-Gaussian posterior is well-known to be near-Gaussian — Brown & Maydeu-Olivares 2011/2012, Heister et al. 2025.)
- **Block model:** `@choice` block from compiled JSON = one Thurstonian forced-choice block, size n ∈ [2, 4]. n=2 case is closed-form single-variable probit; n=3/4 extend via multivariate normal CDF.
- **Testlet unit:** `(user_id, story_id)` — random effect `ζ_us ∈ ℝ⁶`, prior `N(0, σ²_testlet · I_K)` with `σ²_testlet = 0.25`. Episode-level too sparse; novel-level too coarse.
- **Testlet lifecycle:** no decay, no zeroing; old `ζ_us` reused as init when user returns to a story. Joint MAP over (θ, ζ) per event.
- **Confidence → ψ² coupling (BRM novelty):** `ψ_i² = ψ_min² + (ψ_max² − ψ_min²)·(1 − c_i)^γ`, defaults `ψ_min² = 0.25`, `ψ_max² = 4.0`, `γ = 2`. Confidence enters likelihood as inverse-variance on option uniqueness, **not** as a prior on the loading vector.
- **Low-confidence skip floor:** `TAU_LIKELIHOOD_MIN = 0.1`. Below this on all options in a block → event marked `skipped_no_tag`.
- **Clamping:** θ per-dim clipped to `[-4, 4]`; `diag(Σ_θ)` clipped to `[1e-4, 1e2]`.
- **Cold-start prior:** `θ ~ N(0, I_6)`. If [[concepts/dream-rec-component-5-cold-start]] questionnaire ran, that informative prior is read once and not recomputed here.
- **Joint prior shape:** 5 trait axes share dense `Σ_5_init = I_5`; agency axis independent in prior (`σ²_a_init = 1`). Block-diagonal joint Σ; posterior may correlate via data.

## Sharpness (testlet-aware)

`sharpness = 1 / mean(diag(Σ_θ))` where `Σ_θ` is the θ-block of the inverse of the (2K)×(2K) joint Hessian. This is mandatory — using marginal posterior precision ignoring ζ underestimates SE 0.03–0.12 (Frick 2023).

Sharpness is **not** normalized; fallback gate at `SHARPNESS_FALLBACK = 0.5` (already wired in `app/routes/recommend.py`).

## Signature contract change

Current `update_theta(db, *, user_id, story_id, item_tag, selected_option_id)` passes only the selected option's `ItemTag`. Implementation must extend to `list[ItemTag]` (the full block) + `selected_option_id` — Thurstonian forced-choice likelihood needs every option's loading + confidence.

## Algorithm sketch

```
prior_mean, prior_cov ← user_global_theta.theta_mean, theta_cov
zeta                  ← user_global_theta.story_random_effects.get(story_id, 0_vec)
loadings, psi2, conf  ← derive_from_item_tags(block)   # §6 mapping
(theta_map, zeta_map) ← newton_raphson(joint_neg_log_post, init=(prior, zeta),
                                       max_iter=10, tol=1e-5)
H            ← hessian(joint_neg_log_post, at=(theta_map, zeta_map))   # (2K)×(2K)
posterior_cov ← inv(H)[:K, :K]                                          # marginalize ζ
write user_global_theta: mean, cov, story_random_effects[story_id], sharpness
```

Cholesky solves on each Newton step (no `inv()` direct); ridge fallback `H + ε·I` on non-PD Hessian; convergence by Δθ L∞ < 1e-5 or max_iter=10 (warning on overrun, event still processed).

## Failure modes

| Trigger | Action |
|---|---|
| Hessian non-PD | Add `1e-3·I` ridge, retry; warning; event processed |
| Newton no-convergence | Accept last step; warning |
| θ NaN/Inf | Rollback transaction; event `failed`; previous theta preserved |
| `schema_version` mismatch (item vs user) | Event `failed`, error="schema_version_mismatch" |
| All-option `c_i < TAU_LIKELIHOOD_MIN` | Event `skipped_no_tag`; θ untouched |
| Only 1 active option in block | Event `skipped_no_tag` |
| `selected_option_id` not in block | Event `failed`, error="selected_option_not_in_block"; no retry |

## Performance budget

- `update_theta` < 50ms incl. DB I/O; Newton inner loop < 5ms for K=6, n ≤ 4
- End-to-end `POST /events/choice` < 200ms
- JSONB cov: ~300 bytes/user

## What's deliberately NOT done

- Item parameters `{λ_i, ψ_i²}` are fixed input from `ItemTag`. Loop A (P2) will make them updatable.
- Multivariate normal CDF code path for n=3, n=4 implemented but most blocks are n=2 (closed-form).
- No `last_event_id` field added to `UserGlobalTheta` (kept compatible with current schema).

## Cross-links

- [[concepts/dream-rec-integration-architecture]]
- [[concepts/dream-rec-component-2-llm-tagger]] — produces loadings + confidence
- [[concepts/dream-rec-component-3-genre-projection]] — consumes θ posterior
- [[concepts/dream-rec-component-5-cold-start]] — seeds informative prior
