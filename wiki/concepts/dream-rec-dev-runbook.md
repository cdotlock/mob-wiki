---
title: dream-rec dev runbook
updated: 2026-05-24
tags: [dream-rec, runbook, dev, recommendation]
status: shipped
---

# dream-rec dev runbook

How to take the dream-rec recommendation service from a fresh checkout to a verified end-to-end run on a local machine. Covers (a) standalone dream-rec smoke (HTTP + Postgres only), (b) real-LLM tagger smoke (burns mob-ai credit), (c) cross-repo wire from lunaverse-backend.

System overview: [[concepts/dream-rec-integration-architecture]]. Sub-components: [[concepts/dream-rec-component-1-tirt-estimator]], [[concepts/dream-rec-component-2-llm-tagger]], [[concepts/dream-rec-component-3-genre-projection]], [[concepts/dream-rec-component-4-dream-ranker]], [[concepts/dream-rec-component-5-cold-start]].

## Prereqs

- Python 3.12 + [uv](https://github.com/astral-sh/uv) at `$HOME/.local/bin/uv`
- Local Postgres 16 reachable at `postgresql://postgres:postgres@localhost:5432/noval_demo` (NOT `lunaverse` — the schema-version sample in `.env.example` is misleading)
- `~/.config/<repo>/.env` populated from `.env.example` with at minimum:
  ```
  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/noval_demo
  DREAM_REC_PORT=8766
  DREAM_REC_BEARER=dev-secret-change-me
  MOB_AI_BASE_URL=https://ai.mob-ai.cn/v1
  MOB_AI_API_KEY=<from sibling assets-produce .env>
  LLM_TAGGER_MODEL=claude-sonnet-4-6
  ```
- `git` access to `AugustZAD/dream-rec` (user's namespace)

## Bootstrap

```bash
cd ~/MobAI/dream-rec
uv sync                                 # install Python deps
PATH="$HOME/.local/bin:$PATH" \
  uv run alembic upgrade head           # apply 0001 → 0002 → 0003
PATH="$HOME/.local/bin:$PATH" \
  uv run pytest -q                       # 367 tests should pass
PATH="$HOME/.local/bin:$PATH" \
  uv run ruff check app tests scripts    # clean
```

## A. Standalone dream-rec smoke (no LLM, no lunaverse-backend)

This is the cheapest path to verify the system runs.

### A1. Seed dev data

```bash
PYTHONPATH=. PATH="$HOME/.local/bin:$PATH" \
  uv run python scripts/seed_dev_dreams.py
```

Creates:
- 1 `GenreProjection(genre="general")` with 6×6 identity matrix — without this, `/recommend` falls back to popularity proxy (`w_personal=0`).
- 6 `DreamSignature` rows with carefully chosen axis_position / engagement / age permutations.
- 2 `ItemTag` rows for choice block `(novel=22222222-..., episode=33333333-..., step-1)` with options `a` (active/novel) and `b` (warm/intimate). Without these, `/events/choice` skips with `SKIPPED_NO_TAG`.

Default `novel_id` is `22222222-3333-4444-5555-666666666666` — used by all the smoke recipes below. Override via CLI arg.

### A2. Start the service

```bash
PATH="$HOME/.local/bin:$PATH" \
  uv run uvicorn app.main:app --port 8766 --host 127.0.0.1 \
  > /tmp/dream-rec.log 2>&1 &
sleep 3
curl -sf http://127.0.0.1:8766/health
# {"status":"ok","schema_version_active":"v1.0.0","outbox_pending":0,...}
```

### A3. Exercise endpoints

```bash
BEARER="dev-secret-change-me"
USER=11111111-2222-3333-4444-555555555555
NOVEL=22222222-3333-4444-5555-666666666666
EP=33333333-4444-5555-6666-777777777777

# Cold start: 5 binary-choice items, write informative prior
curl -s "http://127.0.0.1:8766/cold-start/items?schema_version=v1.0.0" \
  -H "Authorization: Bearer $BEARER" | jq '.items | length'  # → 5

# Submit cold-start (all answers "a")
curl -s -X POST "http://127.0.0.1:8766/cold-start/submit" \
  -H "Authorization: Bearer $BEARER" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER\",\"schema_version\":\"v1.0.0\",\"responses\":[
    {\"item_id\":\"cs-1\",\"selected_option_id\":\"a\"},
    {\"item_id\":\"cs-2\",\"selected_option_id\":\"a\"},
    {\"item_id\":\"cs-3\",\"selected_option_id\":\"a\"},
    {\"item_id\":\"cs-4\",\"selected_option_id\":\"a\"},
    {\"item_id\":\"cs-5\",\"selected_option_id\":\"a\"}
  ]}"

# Read theta
curl -s "http://127.0.0.1:8766/theta/$USER" \
  -H "Authorization: Bearer $BEARER" | jq '.theta_mean,.sharpness,.choice_count'

# Fire a TIRT update via /events/choice (matches the ItemTag block seeded in A1)
curl -s -X POST "http://127.0.0.1:8766/events/choice" \
  -H "Authorization: Bearer $BEARER" \
  -H "Content-Type: application/json" \
  -d "{\"idempotency_key\":\"$(uuidgen)\",\"user_id\":\"$USER\",\"novel_id\":\"$NOVEL\",
        \"episode_id\":\"$EP\",\"story_id\":\"$NOVEL\",\"choice_step_id\":\"step-1\",
        \"selected_option_id\":\"a\"}"

# Recommend — should return 6 ranked dreams
curl -s "http://127.0.0.1:8766/recommend?user_id=$USER&novel_id=$NOVEL&schema_version=v1.0.0" \
  -H "Authorization: Bearer $BEARER" | jq '.items[] | {dream_id,score,axis_match,engagement,freshness}'
```

Expected ranking with the seeded dreams: `dream-perfect-match` first (score ≈ 0.86, axis_match 0.93, fresh 0.97). `dream-opposite` last (score ≈ 0.25, axis_match 0.05).

### A4. Cleanup

```bash
kill %1   # stop uvicorn
```

## B. Real-LLM tagger smoke (burns mob-ai credit)

Verifies the LLM tagger actually produces sensible loadings against the mob-ai gateway.

```bash
PYTHONPATH=. PATH="$HOME/.local/bin:$PATH" \
  uv run python scripts/smoke_real_llm_tag.py
```

What it does:
1. Loads `tests/fixtures/compiled_simple.json` (2-option choice: polite/safe vs sarcastic/brave).
2. Mocks `BackendClient` so no lunaverse-backend needed.
3. Calls `tag_novel()` with real `LLMClient` → 1 chat completion to `claude-sonnet-4-6`.
4. Reads back the resulting `ItemTag` rows and prints loadings.

Expected output (loadings will vary on rerun even at temp=0):

```
[smoke] PASS
  option=A  conf=0.75  status=auto_accepted
    attachment +0.60   affect +0.40   sensation -0.50   ...
  option=B  conf=0.75  status=auto_accepted
    sensation +0.60    agency +0.50   attachment -0.60  ...
```

### Known gateway gotcha

mob-ai gateway fingerprints on User-Agent and blocks the default OpenAI SDK signature with `Your request was blocked.` — `LLMClient.from_settings()` overrides `User-Agent: dream-rec/0.1.0` to bypass. If you see `PermissionDeniedError: Your request was blocked.`, check that this header override is intact.

## C. Cross-repo wire from lunaverse-backend

Verifies `app/services/dream-rec-client.ts` in lunaverse-backend can talk to dream-rec.

```bash
# Terminal 1: dream-rec
cd ~/MobAI/dream-rec
PATH="$HOME/.local/bin:$PATH" \
  uv run uvicorn app.main:app --port 8766 --host 127.0.0.1

# Terminal 2: lunaverse-backend smoke
cd ~/MobAI/lunaverse-backend
DREAM_REC_ENABLED=true \
DREAM_REC_URL=http://127.0.0.1:8766 \
DREAM_REC_BEARER=dev-secret-change-me \
node_modules/.bin/tsx _local_tools/dream-rec-client-smoke.ts
```

(Use `node_modules/.bin/tsx` not `pnpm tsx` — `pnpm` first runs `pnpm install` which trips on `@prisma/client` ignored-builds. The binary directly works.)

Expected:
```
[smoke] /health status=200
[smoke] postChoiceEvent fired
[smoke] postTagNovel + postTagDream fired
[smoke] /theta status=200  choice_count=6
[smoke] DONE
```

Note: `postTagNovel` and `postTagDream` will accept-200 from dream-rec but their BackgroundTasks then try to call back to `:3000`/api/internal/... — that fails with `ConnectError` since lunaverse-backend isn't running in this smoke. Harmless for verifying the wire.

## Files of interest

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app factory |
| `app/routes/` | endpoint handlers |
| `app/services/llm_tagger/` | C2 LLM tagger package |
| `app/services/tirt/` | C1 Bayesian estimator |
| `app/services/genre_projector/` | C3 projection |
| `app/services/ranker/` + `app/services/dream_ranker.py` | C4 scorer |
| `app/services/cold_start/` | C5 questionnaire |
| `app/workers/outbox.py` | background retry of failed/pending choice events |
| `scripts/seed_dev_dreams.py` | dev data for /recommend |
| `scripts/smoke_real_llm_tag.py` | one-off real-LLM smoke (costs money) |
| `alembic/versions/0001_initial_schema.py` → `0003_cold_start_tables.py` | migrations |
| `tests/fixtures/compiled_simple.json` | minimal 2-option choice for tagger tests |

## When something is wrong

| Symptom | Probable cause |
|---|---|
| `asyncpg.InvalidCatalogNameError: database "lunaverse" does not exist` | `.env` `DATABASE_URL` still points at canonical `lunaverse` instead of local `noval_demo`. Fix the local `.env`. |
| `/recommend` returns `axis_match=0.5, engagement=0.5, used_fallback=true` | (a) `GenreProjection(genre="general")` not seeded → `used_cold_start_matrix=true` → `w_personal=0`. (b) `engagement_stats` JSONB keys not camelCase (`completionRate`/`replayRate`/`exitRate`). Run `scripts/seed_dev_dreams.py`. |
| `/events/choice` returns `SKIPPED_NO_TAG` | No `ItemTag` block with ≥2 options for that `(novel, episode, choice_step)`. Seed via `scripts/seed_dev_dreams.py` (creates option a + b for `step-1`). |
| `PermissionDeniedError: Your request was blocked.` from mob-ai | Gateway fingerprinted the OpenAI SDK UA. Confirm `LLMClient.from_settings` still sets `default_headers={"User-Agent": "dream-rec/0.1.0"}`. |
| `pnpm tsx` in lunaverse-backend tries to reinstall | Use `node_modules/.bin/tsx` directly. |

## References

- Repo: [AugustZAD/dream-rec](https://github.com/AugustZAD/dream-rec)
- Spec: `docs/superpowers/specs/2026-05-23-dream-rec-integration-architecture-design.md`
- Plan: `docs/superpowers/plans/2026-05-23-dream-rec-integration-architecture.md`
- Cross-repo client (in lunaverse-backend, local only): `app/services/dream-rec-client.ts`
