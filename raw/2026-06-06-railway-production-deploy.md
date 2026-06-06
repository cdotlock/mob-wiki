---
title: 2026-06-06 Railway Production Deploy — MSS realignment cutover (zero-data-loss)
date: 2026-06-06
---

# 2026-06-06 Railway Production Deploy

Source record for the production deploy that landed the MSS-realignment cutover (and four
co-shipped features) onto Railway production with zero data loss. Captured by the agent that
ran the deploy. This is the immutable provenance for `wiki/concepts/railway-production-deploy.md`.

## What shipped (HEAD = `6d378ea0` on `main`)

- **MSS realignment cutover** — the new MSS contract that deletes the influence subsystem,
  goto/label, CG sub-steps, the 3-slot stage, and `Session.resolvedInfluences`; single-sprite
  stage (MC-left / others-right). The spec side is documented in
  `concepts/mss-spec-redesign-2026-06`; this deploy is the *consumer cutover* reaching prod.
- **Player Soul-Memory dark-launch** — per-player soul+memory plumbing for the Dream agent,
  feature flags default OFF (no behavior change in prod until flipped).
- **TLWB (the-lives-we-borrow) listed as a 2-player co-op** in the prod catalog, including the
  multi-ending room finalize loop fixed 2026-06-05.
- **second-chorus "Sera" migrated to the new MSS spec** + TTS regenerated (16 episodes,
  3196 lines) + no-romance fallback routed to highest-affection LI.
- **Recommended-novels endpoint** `/api/users/me/novels/recommended` for home/discovery.

Co-shipped deploy-mechanics commits (this session):

- `aacaea7c` — ci(deploy): switch Railway auth to `RAILWAY_API_TOKEN` (account)
- `fad2ed4a` — ci(deploy): scope seed-hash railway calls + make step-22 best-effort
- `6d378ea0` — docs(runbook): `RAILWAY_TOKEN` → `RAILWAY_API_TOKEN` for railway commands

## Topology (confirmed)

- Railway project `51635187-c76b-4fd0-8a32-870d28042bd5`, environment `production`.
- Services behind a `gateway` reverse proxy (public `https://app.moonshort.ai` →
  `app.railway.internal:3000`): `app` (Next.js), `worker` (BullMQ/pgmq processor), `tts`,
  `dream-agent`, `dream-rec`. Worker service ID `358d77ca-c5f4-4688-802d-8311293a9d95`;
  gateway service ID `0e48f07a-1f7a-4ab0-9a33-0c6ff820ab7a`.
- Prod DB = Supabase project `sujmoojhppnnelsqwpcm` (US, aws-1-us-west-1). `DATABASE_URL` =
  session-mode pooler (port 5432); `DIRECT_URL` = `db.sujmoojhppnnelsqwpcm.supabase.co`.
- Deploy account token: `RAILWAY_API_TOKEN` (853583725@qq.com), in `~/.zshrc` and mirrored as a
  GitHub Actions secret of the same name.

## The Railway CLI auth regression (root cause of two failed runs)

A Railway CLI version bump (~2026-06-05) changed `railway up` to **reject the project token
`RAILWAY_TOKEN`** with `Not signed in`, while `railway run` and `railway variables` still
accept it. Effect: a project-token deploy passed every early step and then died at the
"Deploy app" step.

Fix: the deploy workflow now authenticates with the **account token `RAILWAY_API_TOKEN`**
(GH secret set under the same name, `aacaea7c`). The account token has no implicit project
scoping, so the two seed-hash `railway variables` calls (read previous / update hash) needed
explicit `--project`/`--environment` flags, and the "Update seed hash" step was made
best-effort with `if/else` so a cosmetic failure there no longer skips the health probe and
the three functional smokes (`fad2ed4a`). `--skip-deploys` is incompatible with the legacy
`--set` form (usage error) — do not add it.

Canonical green deploy: GitHub Actions run `27035271255` (~12 min, all 3 functional smokes
passed).

## Zero-data-loss strategy (no DDL applied to prod at all)

The realignment is a breaking schema change, so the deploy had to land it without dropping
data. Mechanics:

1. Prod is **`db push`-managed**: the `_prisma_migrations` table does not exist on prod, so an
   in-CI `prisma migrate deploy` always fails P3005. `skip_migrations=true` is therefore
   **mandatory** for this prod. (Independently, GH runners are IPv4-only and Supabase's direct
   host is IPv6-only, so CI would migrate through the session-mode pooler, which caps at 15
   clients — unreliable once app+worker saturate it.)
2. Built the merged deploy schema (`node scripts/build-deploy-prisma-schema.cjs` — concatenates
   the main 35-model schema + the services/dream 8-model schema into one) and ran
   `prisma migrate diff` against the live prod DB. Result: **prod is already a superset of
   HEAD's schema needs.** The only difference was two legacy `NovelCharacter` column drops
   (`displayName`, `isProtagonist`) that prod still carries (dropped on dev, deferred on prod).
3. **Deliberately did NOT apply those drops.** The deploy ran additive-only + content-only
   seed; no DDL was executed against prod. 105 `User` rows untouched.

## Verification matrix (all green)

- Health: `GET https://app.moonshort.ai/api/health` → `{code:0, data:{status:healthy, db:ok,
  queueBackend:pgmq, queueConnectivity:ok}}`.
- Catalog: 9 novels live.
- Episode content: 226/226 episodes across all branches validated as post-realignment new-spec
  (no forbidden step types: char_hide/char_look/char_move/phone_hide/music_play/
  music_crossfade/music_fadeout/sfx_play/label/goto; no removed fields: char_show.position /
  pause.clicks / cg_show.steps).
- DB contracts: `db:assert-contracts` passed (9 CHECKs / 46 indexes / 3 functions / 15 triggers).
- TTS warmth: 4 voiced novels (villain-season, second-chorus, the-lives-we-borrow,
  dont-pretend-with-us); `EpisodeTTSAsset` row counts match the dev fixtures; 0 cold episodes.
  Warmth is DB-row-gated on `(novelId, episodeSlug, stepId)`, not R2-object-gated.
- Schema: prod confirmed a superset of HEAD; user data untouched.

Seed hash stamped on the app service: `LAST_SEED_HASH =
3fd61e8dcf172005bcc12bdd9b43fdfece534c7cb498bd6563d70b5b843afc0e`.

## Not exhaustively tested (non-blocking, noted at handoff)

- Live 2-player co-op room mechanics (needs two concurrent clients; dev-verified previously).
- Stripe moons prices (out of scope this deploy; untouched).
- Cocos frontend (separate v5 migration handoff doc, `fe4ba9cf`).
