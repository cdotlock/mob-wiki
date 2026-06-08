---
title: dream-rec Component 6 — Three-Loop A/C/B Dashboard design
updated: 2026-05-24
tags: [dream-rec, dashboard, component-6, recommendation, observability]
sources: [docs/superpowers/specs/2026-05-23-dream-rec-component-6-dashboard-design.md]
status: deferred
---

# dream-rec Component 6 — Three-Loop A/C/B Dashboard

Internal observation surface for PMs and research scientists on the three calibration loops of the recommendation system (A: persona inference quality, C: content engagement, B: matching quality). Streamlit app on port 8767 that reads `dream_rec` schema directly + cached materialized views. **Deferred** — design locked but not implemented as of 2026-05-24; depends on `recommend_log` and `dream_play_snapshot` tables which Component 0 schema does not yet include.

See [[concepts/dream-rec-integration-architecture]] for Component 0 wiring. Component 6 closes Component 0 §9 O9.

## Decisions locked

- **Stack:** Streamlit (Python-native, matplotlib/arviz for IRT info curves and reliability diagrams). Grafana/Superset rejected — they can't render Cronbach α, Fisher information curves, or calibration plots natively.
- **Audience:** dream-rec team + lunaverse PM/research. **Authors** do not see this dashboard — their feedback goes through a separate Author Workbench (backlog item).
- **Separation from `/health`:** the FastAPI `/health` endpoint stays a machine-read liveness probe. Dashboard is a separate Streamlit process, reuses `/health` fields for its system-health panel only.
- **Data source:** direct read on `dream_rec` schema + materialized views for heavy recomputed metrics + a daily cron-pulled `author_funnel_snapshot` from lunaverse `/api/internal/dream-rec/funnel`. No external OLAP / warehouse — single PG instance is enough at P0/P1 scale.
- **Refresh cadence:** Loop A daily MV (02:00), Loop B/C weekly MV (Monday 03:00), system-health real-time. `REFRESH MATERIALIZED VIEW CONCURRENTLY` to avoid lock contention.
- **Deployment:** same container as dream-rec, binds 127.0.0.1:8767. Auth via independent `DASHBOARD_BASIC_AUTH_USER/PASS` (separate token rotation from `DREAM_REC_BEARER` so PMs can be granted temporary view access). Nginx reverse proxy or VPN allowlist.
- **Alerts:** Loop A red lines + system-health → Slack `#dream-rec-alerts` webhook (5-min poll). Loop B/C → daily email digest only (low recency value, high noise risk).
- **MVP scope:** Loop A full + system-health full + Loop B three core metrics (B1, B2, B3) + Loop C placeholder for dream-level completion/replay. Author retention deferred to P1. Cold-start ramp deferred until Component 5 has running data.

## Loop A — persona inference quality (P0)

| Metric | Computation | Red line |
|---|---|---|
| A1 Cronbach α per axis | aggregate user choices on items with `|loading| ≥ 0.5` on the axis | α < 0.5 (instrument broken) |
| A2 IRT item-information curves | `I_i(θ) = Σ_o p_o(θ)·(∂log p_o/∂θ)²`, written by Component 1 TIRT to `item_info_snapshot` | min(I) at `|θ| ≤ 1` < 0.1 |
| A3 LLM calibration / reliability | 10-bin confidence vs human-review approval rate | ECE > 0.15 |
| A4 Auto-accept / review queue | daily counts of `auto_accepted` / `pending_review` / `human_approved/rejected` + aging | `aging_7d / pending > 0.3` |
| A5 Heteropolar scene coverage | unresolved + resolution-time from `scene_coverage_flag` | unresolved > 50 for 14 days |

## Loop B — matching quality (P0 observation only, no closed-loop refit)

| Metric | Notes |
|---|---|
| B1 axis_match × engagement correlation | requires new `recommend_log` table |
| B2 fallback vs personalized completion uplift | A/B by `used_fallback` |
| B3 sharpness distribution + fallback rate | bucketed histogram, daily |

Loop B explicitly does **not** auto-refit `M_genre` — observation only at P0; refit lives in P2.

## Loop C — content engagement (P0 placeholder)

| Metric | Status |
|---|---|
| C1 genre × axis-bin × completion heatmap | needs `dream_play_snapshot` from lunaverse puller |
| C2 author retention by engagement tier | deferred to P1 |
| C3 cold-start ramp | deferred until Component 5 produces data |

## Required new tables (write owners explicit)

- **`dream_rec.recommend_log`** — every `GET /recommend` response, ranked items + score breakdown. Owner: `app/routes/recommend.py` writes; Loop B reads.
- **`dream_rec.dream_play_snapshot`** — pulled from lunaverse daily by `workers/loop_c_puller.py`. Owner: dashboard cron writes; ranker reads via `DreamSignature.engagement_stats` aggregation.
- **`dream_rec.author_funnel_snapshot`** — pulled from lunaverse `/api/internal/dream-rec/funnel`. Owner: dashboard cron writes; Loop C reads.
- **`dream_rec.item_info_snapshot`** — written by Component 1 TIRT when item params change; dashboard reads.

## Streamlit layout

```
streamlit_app/
├── Home.py                  # 4 loop KPI tiles + status badges
├── pages/
│   ├── 1_Loop_A_Persona.py
│   ├── 2_Loop_B_Matching.py
│   ├── 3_Loop_C_Content.py
│   ├── 4_System_Health.py
│   └── 5_Explorer.py        # per-user / per-dream / per-novel drill
└── lib/
    ├── db.py
    ├── queries.py
    └── plots.py
```

Each page has `schema_version` and time-window selectboxes — metrics never mix across schema versions.

## Cross-repo contract (lunaverse)

lunaverse exposes `/api/internal/dream-rec/funnel` (read-only). dream-rec dashboard cron pulls daily (03:00). Push from lunaverse rejected — cadence must stay dream-rec-controlled.

## What's deliberately NOT done at MVP

- Loop B M_genre auto-refit (waits for P2 — feedback loop too weak before then)
- Loop C author retention (waits for lunaverse funnel API)
- P/E grade alerts (no PagerDuty — team size doesn't justify it)
- BI-style slice-and-dice (Superset would be better; dream-rec's needs are psychometric, not BI)
- IRT info-curve auto-anomaly detection (relies on A1 as cheap fallback signal)

## Cross-links

- [[concepts/dream-rec-integration-architecture]]
- [[concepts/dream-rec-component-1-tirt-estimator]] — writes `item_info_snapshot` consumed by A2
- [[concepts/dream-rec-component-2-llm-tagger]] — `confidence` field consumed by A3 calibration
- [[concepts/dream-rec-component-3-genre-projection]] — `loop_b_touched` flag consumed by B1
- [[concepts/dream-rec-component-4-dream-ranker]] — `score_breakdown` written into `recommend_log` for B1
