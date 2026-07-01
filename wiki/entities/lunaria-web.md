---
title: lunaria-web
updated: 2026-07-01
---

# lunaria-web

A **web tool for creating playable interactive stories** (Lunascript `.ls`) with an AI
co-writer — the browser counterpart to the desktop Lunaverse IDE. Node backend
(`lunaria-server`) serves the SPA (`lunaria-web`) and proxies auth + AI to the Lunaverse
gateway (`app.moonshort.ai`). Repo: `AugustZAD/lunaria-web` (pnpm monorepo:
`lunaria-web` React 18 SPA, `lunaria-server` Node, shared `@lunaverse-ide/shared`,
`player-core`).

## Architecture

- **SPA**: React 18 + Radix + lucide + CSS-variable **cream** design tokens (Fraunces +
  Inter). Bundled by **esbuild** (single IIFE, CSS inlined) via
  `scripts/build-extension.mjs` — **no Vite/Tailwind**. TS NodeNext ESM (local imports end
  `.js`). Tests: vitest, node env, SSR via `renderToStaticMarkup` (no testing-library).
- **Server**: framework-free Node `http`; pure router (`handlers.ts`) + socket layer
  (`server.ts`). Project store on disk (`LUNARIA_ROOT`). Compiles via the local `lsc`
  binary (`LS_BIN`) — free, no gateway cost.
- **Auth = the IDE model**: `POST /api/auth/login {username,password}` → token; the
  **login token IS the gateway key** for AI (no provider key stored). Guest mode
  (`token=dev`) unlocks all non-AI paths locally. See
  [[entities/lunaverse-ide]], [[concepts/ls-format]].

## Core capabilities (2026-07-01 completion pass — 6 gaps closed)

- **Onboarding**: a single composer box — describe with AI, or **drag/attach a `.txt`/`.md`
  novel to adapt** (`POST /api/projects/:id/adapt` splits chapters server-side → agent
  writes ch.1). Multiple **books** (topbar project switcher + New book); last book restored
  across sessions.
- **Editor**: Notion-like **card view is the default** (code is a toggle) — hover **+**
  add-block menu, **dnd-kit** drag reorder of top-level blocks, delete; every edit is a
  minimal line-level source patch (round-trip safe via `ls/edit-source.ts` + `emit-block`).
- **Canvas**: two levels — story map → double-click → per-step 分镜 graph (D20 check
  renders as a dice node). Compiled locally.
- **Assets**: bind / **generate** (images) / **upload** (any kind; audio music/sfx is
  upload-only). Guests upload/bind; AI generation gated behind a real login. (Audio
  upload/bind/persist complete; shared `stage-player` still no-ops audio playback.)
- **Agent sidebar**: persistent script-scoped co-writer; fixed tool whitelist
  (list/read/write/compile scene, list assets). The forked `.ls` authoring **skills**
  (`.claude/skills/*/SKILL.md`) are composed into its system prompt. Cutoff + collapse fixed.
- **Preview**: steps the compiled episode in the real player engine; `asset://` refs
  rewritten to authed object URLs.
- **i18n**: runtime-switchable **zh / en** (中/EN toggle), dependency-free React context;
  product named plainly **"Lunaria"** (no otome/乙女). Design doc: `DESIGN.md`.

## Gateway findings (VERIFIED LIVE 2026-07-01, funded `vito` login)

- **Text model**: the login-token gateway (`/api/ide/v1`) exposes `gpt-5.5:free` /
  `claude-opus-4-6:free`. It **does NOT expose deepseek** — `deepseek-chat:free` and
  `deepseek-v4-flash:free` both HTTP 500 on the first call (deepseek is IDE-only via direct
  `api.deepseek.com` + a key). Default `LUNARIA_MODEL=gpt-5.5:free`; full agent loop
  (list→write→self-correct→compile→done) verified working live.
- **Style catalog**: `GET /api/ide/styles` (login token, `style:read`) fetched live
  (source "gateway", 5-min cache); builtin fallback offline/guest.
- **Image gen — WORKS end to end, WITH style references (verified)**: `POST {gateway}/api/ide/
  tools/generate-image-gpt` (login token; charges `pointConsume`). Real 1024×1024 PNG
  generated (img2img with the style ref), downloaded, stored — verified with
  Kyoto_Animation. Notes: (1) **img2img is NOT broken** — an earlier Arcane stall
  (`progress:10` forever) was that style being **edited server-side** (its ref temporarily
  unusable); a healthy style generates fine. We send a proper https ref URL and the style
  wiring is correct. Style refs are **ON by default** (matches IDE); `LUNARIA_IMAGE_USE_STYLE_REFS=0`
  forces text-to-image. (2) The result OSS host **omits its intermediate TLS cert** (undici
  `UNABLE_TO_GET_ISSUER_CERT`, curl works) → the image **download** falls back to
  `node:https` with relaxed chain verification (that download only; auth/LLM/submit/poll
  stay verified). Poll window tunable (`LUNARIA_IMAGE_POLL_ATTEMPTS`/`_INTERVAL_MS`, 60×5s;
  `LUNARIA_IMAGE_DEBUG=1`). Submit/poll/parse is byte-for-byte identical to assetctl
  `internal/tools/gpt`.

## Status

All six requested gaps closed + real image gen (incl. style img2img) confirmed,
browser-verified. ~461 unit tests green (web 269 + server 192). On `main` @
`AugustZAD/lunaria-web`. Deploy notes in `DEPLOY.md`. Related: [[entities/lunaverse-ide]],
[[concepts/ls-format]], [[concepts/four-layer-philosophy]].
