---
title: dream-rec Component 3 — Genre projection design
updated: 2026-05-24
tags: [dream-rec, genre-projection, component-3, recommendation]
sources: [docs/superpowers/specs/2026-05-23-dream-rec-component-3-genre-projection-design.md]
status: shipped
---

# dream-rec Component 3 — Genre projection

Projects the user's 6-d global persona `θ` onto a per-genre `K_genre`-d subspace (`z_g = M_g · θ`) so [[concepts/dream-rec-component-4-dream-ranker]] can score `axis_match` in the same space as `DreamSignature.axis_position`. The hybrid build strategy (manual seed + data-driven PCA refinement) keeps cold-start sane while letting per-genre data steer the matrix over time.

See [[concepts/dream-rec-integration-architecture]] for Component 0 wiring.

## Decisions locked

- **Shape:** `M_g ∈ ℝ^{K_genre × K_global}`, row-major JSONB `{rows, cols, data}`. Corrects Component 0 schema comment (`K_global × K_genre`) to `K_genre × K_global` — the projection contracts, output dim first.
- **K_genre bound:** `1 ≤ K_genre ≤ 3`. Most genres K=1 (single main axis), a few K=2 (main + secondary), K=3 only as escape hatch.
- **Element type:** signed float. Negative weights allowed (e.g. horror's bipolar "slow-dread ↔ jump-scare").
- **Normalization:** rows L2-normalized (each genre-axis is a unit vector); columns left unnormalized to preserve θ scale.
- **Build strategy:** **Hybrid** (manual seed + PCA refinement). Pure-manual doesn't scale; pure-PCA is noise-dominated in cold-start. Blend `M_new = (1−α)·M_manual + α·M_pca` with `α = min(0.7, N/5000)`.
- **PCA gating thresholds:** `N_items ≥ 1500`, `N_users ≥ 200`, `confidence_avg ≥ 0.6` (all three must hold to enter hybrid). `α_max = 0.7` — always preserves ≥30% of manual seed.
- **Cold-start matrix:** identity-on-5-core-axes (drops play_style). `seeded_from = "cold_start_identity_5core"`. Full 6×6 identity rejected because play-style would pollute trait-based matching.
- **Versioning:** `matrix` strongly bound to `schema_version`; schema bump triggers all-genre re-seed.
- **Swap-in:** shadow row (`is_active=false`) → A/B for ≥7 days → activate via `UNIQUE(genre, schema_version, is_active)` switch; old row never deleted.
- **Pre-write validation:** SVD condition number `κ < 50`, no NaN/Inf, dims match `rows`/`cols` lengths, axis names exist in active schema. Otherwise reject + warn.
- **Failure runtime:** NaN/Inf in `project()` → fall back to cold-start identity.

## Data model (JSONB encoding)

```json
{
  "rows": ["attachment"],
  "cols": ["openness", "sensation", "cognition", "affect", "relational", "play_style"],
  "data": [
    [0.10, 0.55, 0.00, 0.45, 0.70, 0.00]
  ]
}
```

`rows` and `cols` stored explicitly so schema evolution can't silently misalign older matrices.

## Projection (≤10 lines)

```python
def project(theta_dict, projection_row):
    out = {}
    cols = projection_row.matrix["cols"]
    for axis_name, row in zip(projection_row.matrix["rows"],
                              projection_row.matrix["data"]):
        out[axis_name] = sum(row[j] * theta_dict.get(cols[j], 0.0)
                             for j in range(len(cols)))
    return out
```

Missing axes in `theta_dict` → 0 (tolerates partial-migration users).

`z_g` is **not** materialized — recomputed every recommend call (matrix multiply on K_global × K_genre ≤ 18 floats is sub-microsecond).

## Cold-start scenarios

| Scenario | Trigger | Matrix source |
|---|---|---|
| C1 service cold-start | First deploy, zero data | bootstrap seed v1.1 §5.2 genres + identity for the rest |
| C2 unknown genre in query | `/recommend` for genre with no row | runtime identity-on-5-core + async enqueue LLM seed job |
| C3 schema upgrade | `theta_schema_version` bump | all-genre re-seed (§4.1) |

`UserThetaSummary.used_cold_start_matrix: bool` added to `/recommend` response — caller knows the matrix isn't seeded yet. Component 4 ranker drops `axis_match` weight when set.

## Service contract with Component 4

```python
async def project_user_to_genre(db, user_id, genre, schema_version):
    theta = await get_user_theta(db, user_id, schema_version)
    proj  = await get_active_projection(db, genre, schema_version)
    if proj is None:
        proj, is_cold = cold_start_identity_5core(schema_version), True
    else:
        is_cold = False
    z_g = project(theta, proj)
    return z_g, proj.main_axis_def, proj.secondary_axis_def, is_cold
```

## What's deliberately NOT done

- `tertiary_axis_def` schema column — K_genre=3 packs into `secondary_axis_def.additional_axes` for now.
- LLM auto-seed for unknown genres at P0 — log warning, manual seed.
- Per-user genre cache (UserNovelTheta): not needed (compute is cheap, RT bottleneck is DB).

## Cross-links

- [[concepts/dream-rec-integration-architecture]]
- [[concepts/dream-rec-component-1-tirt-estimator]] — produces θ
- [[concepts/dream-rec-component-2-llm-tagger]] — produces ItemTag.loadings used by PCA
- [[concepts/dream-rec-component-4-dream-ranker]] — consumes z_g
