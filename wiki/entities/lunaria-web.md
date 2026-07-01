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
  across sessions. (Fixed "can't start a new book": app was single-project + AI-only
  onboarding.)
- **Editor**: Notion-like **card view is the default** (code is a toggle) — hover **+**
  add-block menu, **dnd-kit** drag reorder of top-level blocks, delete; every edit is a
  minimal line-level source patch (round-trip safe via `ls/edit-source.ts` + `emit-block`).
- **Canvas**: two levels — story map → double-click → per-step 分镜 graph (D20 check
  renders as a dice node). Compiled locally.
- **Assets**: bind / **generate** (images, via live style catalog) / **upload** (any kind;
  audio music/sfx is upload-only — no audio generation). Guests upload/bind; AI generation
  gated behind a real login. NOTE: audio upload/bind/persist is complete but the shared
  `stage-player` still no-ops audio playback by design.
- **Agent sidebar**: persistent script-scoped co-writer; fixed tool whitelist
  (list/read/write/compile scene, list assets) — cannot run code or generate art. The
  forked `.ls` authoring **skills** (`.claude/skills/*/SKILL.md`) are composed into its
  system prompt. Sidebar cutoff + collapse fixed (grid track → 48px rail).
- **Preview**: steps the compiled episode in the real player engine; `asset://` refs
  rewritten to authed object URLs.
- **i18n**: runtime-switchable **zh / en** (中/EN toggle), dependency-free React context;
  product named plainly **"Lunaria"** (no otome/乙女 branding). Design language + user
  flows documented in-repo (`DESIGN.md`).

## Gateway findings (VERIFIED LIVE 2026-07-01, funded `vito` login)

- **Text model**: the login-token gateway (`/api/ide/v1`) exposes `gpt-5.5:free` /
  `claude-opus-4-6:free`. It does **NOT expose deepseek** — `deepseek-chat:free` and
  `deepseek-v4-flash:free` both HTTP 500 on the first call (deepseek is IDE-only via direct
  `api.deepseek.com` + a key). Default `LUNARIA_MODEL=gpt-5.5:free`; full agent loop
  (list→write→self-correct→compile→done) verified working live. Skill guidance trimmed to
  ~1.2k chars/skill to keep the prompt lean.
- **Style catalog**: `GET /api/ide/styles` (login token, `style:read`) works and is fetched
  live (source "gateway", 5-min cache); builtin catalog is the offline/guest fallback.
- **Image gen**: `POST {gateway}/api/ide/tools/generate-image-gpt` (login token; charges
  `pointConsume` so any funded account is authorized). Async submit/poll/parse verified
  correct against real responses; but the provider (`gpt-image2`) can **stall at
  `progress:10 "processing"` for minutes** → the poll window (default 60×5s) is env-tunable
  (`LUNARIA_IMAGE_POLL_ATTEMPTS`/`_INTERVAL_MS`, `LUNARIA_IMAGE_DEBUG=1` logs poll shape). A
  rendered image couldn't be confirmed in-session due to that provider stall (external, not
  a code bug).

## Status

All six requested gaps closed and browser-verified (onboarding/new-book, Notion editor,
agent+skills, live styles, i18n+rename, audio upload). ~461 unit tests green (web 269 +
server 192). On `main` @ `AugustZAD/lunaria-web`. Deploy notes in `DEPLOY.md`. Related:
[[entities/lunaverse-ide]], [[concepts/ls-format]], [[concepts/four-layer-philosophy]].
