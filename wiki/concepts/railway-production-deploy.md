---
title: Railway Production Deploy + Zero-Data-Loss Cutover
tags: [backend, railway, deployment, ci, ops, migration]
sources: [raw/2026-06-06-railway-production-deploy.md]
created: 2026-06-06
updated: 2026-06-06
---

How [[entities/moonshort-backend]] reaches production on **Railway**, end to end: the
service topology, the GitHub Actions deploy workflow, how authentication works (and the CLI
regression that broke it), why in-CI Prisma migrations are skipped, and — most importantly —
the **additive-only "schema superset" cutover** that lands a breaking schema change on a live
DB with zero data loss. This page is the operational complement to
[[concepts/supabase-backend-bootstrap]] (which owns the DB / migration-policy side). The
canonical worked example is the 2026-06-06 MSS-realignment deploy.

## One sentence

Production is **`db push`-managed** (no `_prisma_migrations` table), so deploys ship code +
content while **schema changes are applied operator-side out of band** — and a breaking schema
change is landed only after proving, via `migrate diff` against a merged schema, that prod is
already a **superset** of what the new code needs.

## Topology

| Piece | Value |
|---|---|
| Railway project | `51635187-c76b-4fd0-8a32-870d28042bd5`, environment `production` |
| Public entrypoint | `https://app.moonshort.ai` → `gateway` reverse proxy → `app.railway.internal:3000` |
| Services | `gateway` (proxy), `app` (Next.js), `worker` (queue processor), `tts`, `dream-agent`, `dream-rec` |
| `worker` service ID | `358d77ca-c5f4-4688-802d-8311293a9d95` |
| `gateway` service ID | `0e48f07a-1f7a-4ab0-9a33-0c6ff820ab7a` |
| Prod DB | Supabase `sujmoojhppnnelsqwpcm` (US, aws-1-us-west-1); see [[concepts/supabase-backend-bootstrap]] |
| `DATABASE_URL` | session-mode pooler, port 5432 |
| `DIRECT_URL` | `db.sujmoojhppnnelsqwpcm.supabase.co` (IPv6-only) |
| Storage | shared Cloudflare R2 (asset / TTS audio / episode JSON) — same bucket dev & prod |
| Queue backend | `pgmq` (the prod `/api/health` reports `queueBackend: pgmq`) |

`app` and `worker` share `Dockerfile.railway-app` (`PROCESS_ROLE=app|worker`, entrypoint
`scripts/railway-entrypoint.sh`). Railway injects service variables as Docker build ARGs, so
any `NEXT_PUBLIC_*` that must inline into the client bundle needs both (a) the variable set on
the service and (b) a matching `ARG` in the builder stage. The runner does `pnpm prune --prod`,
so `prisma` and `tsx` are installed globally in the runner image (the worker runs `tsx`,
migrations use the `prisma` CLI).

## The deploy workflow

`.github/workflows/railway-production-deploy.yml`, triggered by `workflow_dispatch`. Inputs:

- **`confirm`** (required) — must be the literal `DEPLOY_PRODUCTION`; a guard against accidental runs.
- **`force_all_services`** (default false) — deploy every service regardless of the path filter.
  Use after infra / base-image changes or a shared-dependency bump.
- **`force_reseed`** (default false) — re-run the post-deploy catalog seed even when the seed
  `.ts` files are unchanged. Use when seed *data* (episode JSON, R2 assets) moved without
  touching the scripts, or to repair drift.
- **`skip_migrations`** (default false) — skip the in-CI Prisma migrate step. **For this prod it
  is effectively mandatory** (see below).

`app` + `worker` are deployed on every run (coupled to the migrate step to prevent a silent
half-deploy where the DB leads the code). The lighter services (`tts` / `dream-rec` / `gateway`
/ `dream-agent`) go through a `paths-filter` and are skipped when unchanged. The filter is
**tip-only** (a `workflow_dispatch` has no base ref, so it diffs HEAD vs HEAD~1) — after a
multi-commit fast-forward merge an auxiliary service can be missed; use `force_all_services=true`
to be safe.

After deploy the workflow runs a health probe + three functional smokes, then stamps the seed
hash. A green run is ~12 minutes.

## Authentication: account token, not project token

Use the **account token `RAILWAY_API_TOKEN`** (853583725@qq.com, in `~/.zshrc`, mirrored as a
GitHub Actions secret of the same name). Regenerate it at
`https://railway.com/account/tokens` — note that is `/account/tokens`, **not** the
project-settings token tab, which issues a project-scoped `RAILWAY_TOKEN` with a different
scope. The short-lived OAuth login (`~/.railway/config.json`) expires with `invalid_grant`;
the account token is the durable path.

### The 2026-06-05/06 CLI regression (important)

A Railway CLI version bump changed `railway up` to **reject the project token `RAILWAY_TOKEN`**
with `Not signed in`, while `railway run` and `railway variables` still accept it. The symptom
is nasty: a project-token deploy passes every early step and then dies at the "Deploy app"
step. The fix, landed this session:

- Switch the workflow's auth to the account token `RAILWAY_API_TOKEN` (commit `aacaea7c`); set
  the GH secret under the same name and remove `RAILWAY_TOKEN` to avoid precedence ambiguity.
- The account token has **no implicit project scoping**, so any `railway variables` / `railway
  run` call must now pass explicit `--project` / `--environment` (and `--service` where
  relevant) flags. The two seed-hash calls were updated accordingly (commit `fad2ed4a`).
- The "Update seed hash" step was made **best-effort** (`if/else`) so a cosmetic failure there
  no longer skips the health probe and the three functional smokes. Do **not** add
  `--skip-deploys` to the legacy `--set` form — it is a usage error.

zsh gotcha: never stuff `railway run` flags into a shell variable (zsh does not word-split an
unquoted variable, producing "unexpected argument"); write them inline.

## Why in-CI migrations are skipped

Two independent reasons, either of which is sufficient:

1. **Prod has no `_prisma_migrations` table.** It is `db push`-managed (see
   [[concepts/supabase-backend-bootstrap]]), so an in-CI `prisma migrate deploy` always fails
   with **P3005** ("database schema is not empty").
2. **The pooler connection cap.** GH runners are IPv4-only and Supabase's `DIRECT_URL` host is
   IPv6-only, so CI would migrate through the session-mode pooler, which caps at 15 clients
   (`EMAXCONNSESSION`). The app+worker steady state already saturates it, so even a no-op
   migrate can fail to get a slot.

Therefore: **apply any schema change operator-side first** (over `DIRECT_URL` from an IPv6 host),
then deploy with `skip_migrations=true` so the gated step is a no-op.

## Zero-data-loss cutover playbook

This is the procedure that landed the breaking MSS realignment without dropping data, and the
template for any future breaking schema change against the live prod DB.

1. **Build the merged schema.** `node scripts/build-deploy-prisma-schema.cjs <out>` concatenates
   the main 35-model schema and the `services/dream` 8-model schema (stripping the dream
   generator/datasource) into one file. Both schemas co-exist in a single Postgres `public`
   namespace, so a main-only schema would mis-diff the dream tables — always diff the merged one.
2. **Diff against live prod.** Run `prisma migrate diff` from the merged schema to the prod DB.
   Read every statement it proposes.
3. **Decide additively.** If the only differences are *drops* (columns/tables the new code no
   longer references), prod is already a **superset** of what HEAD needs — the new code runs
   correctly against the existing schema. Land the deploy **additive-only** and defer the drops.
   On 2026-06-06 the only diff was two legacy `NovelCharacter` column drops (`displayName`,
   `isProtagonist`) dropped on dev but deferred on prod; **no DDL was applied to prod at all.**
4. **Content-only seed.** The post-deploy catalog seed is idempotent upsert of Episode pointers
   (jsonUrl/contentHash); episode JSON + TTS audio live in shared R2, so re-seeding only updates
   rows, never deletes player data. 105 `User` rows were untouched.

A true *destructive* prod cutover (full wipe) is a separate, scheduled, backed-up event and must
use the merged deploy schema after `DROP SCHEMA public CASCADE` + recreate + extensions — never
a bare main-only `db push`, which would drop the `services/dream` tables. That path is the
exception; the additive-only path above is the default.

## Single-novel prod re-seed (no redeploy)

To refresh one novel's content without a full deploy:

```bash
eval "$(grep RAILWAY_API_TOKEN ~/.zshrc)"   # load the account token
railway run --project 51635187-c76b-4fd0-8a32-870d28042bd5 \
  --environment production --service app --no-local -- pnpm seed:<novel>
```

`railway run` injects the prod env (Supabase pooler DB + shared R2) and reads the local repo for
the compiled JSON / mapping; dotenv non-override ensures prod `DATABASE_URL` / `R2_*` win over
the local `.env`. Pre-flight by printing `new URL(process.env.DATABASE_URL).host`. This updates
Episode-row pointers only; it is **not** `railway-production-deploy.yml -f force_reseed` (that
re-runs `railway up`).

## TTS warmth is DB-row-gated, not R2-object-gated

The runtime TTS resolver only honours **Tier-1 `EpisodeTTSAsset (novelId, episodeSlug, stepId)`
rows** — it never probes R2 by object key. Inserting or deleting any step shifts subsequent
`stepId`s, so old prerender rows miss Tier-1 and those lines cold-stream (slow + a flat
heuristic voice). The shared R2 bucket does not save you. The fix is to copy current-stepId
`EpisodeTTSAsset` rows into prod (no re-synthesis needed — audio is content-addressed in R2):
export from dev, import on prod via `railway run`, upsert by natural key. Gate on
`wrong=0 / no-row=0 / objectKey-collision=0`, not on `COLD=0`. See project rule "改已 seed 的剧本必重对 TTS".

## 2026-06-06 worked example — MSS realignment cutover

Shipped at HEAD `6d378ea0`: the MSS realignment consumer cutover (see
[[concepts/mss-spec-redesign-2026-06]] for the contract; the realignment deletes influence /
goto / label / CG sub-steps / 3-slot stage and `Session.resolvedInfluences`), plus four
co-shipped features — Player Soul-Memory dark-launch (flags default off), TLWB listed as a
2-player co-op, second-chorus "Sera" migrated to the new spec + TTS, and the
`/api/users/me/novels/recommended` endpoint. Canonical green run `27035271255`.

Verification (all green): prod `/api/health` `healthy / db ok / queue pgmq ok`; 9-novel catalog;
**226/226 episodes** across all branches validated new-spec; `db:assert-contracts` (9 CHECKs /
46 indexes / 3 functions / 15 triggers); TTS warmth across the 4 voiced novels with row counts
matching dev fixtures and 0 cold episodes; schema confirmed a superset; 105 users untouched.

## Related

- [[concepts/supabase-backend-bootstrap]] — prod DB bootstrap + the "migration = incremental patch, no fresh-replay" policy this page builds on
- [[concepts/mss-spec-redesign-2026-06]] — the MSS contract the realignment cutover carries
- [[entities/moonshort-backend]] — the service this deploys
- [[concepts/production-pipeline-two-phase]] — how content (releases) is written to the DB this deploy seeds

## Sources

- [2026-06-06 Railway Production Deploy](../raw/2026-06-06-railway-production-deploy.md)
