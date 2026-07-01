---
title: lunaria-web
updated: 2026-07-01
---

# lunaria-web

Consumer-facing (C-end) web tool to author interactive otome/visual-novel **Lunascript (`.ls`)** with an AI agent — a stripped-down, browser-native cousin of [[entities/lunaverse-ide]]. pnpm monorepo: `lunaria-web` (React 18 SPA), `lunaria-server` (Node backend), `shared`, `player-core`. Repo `AugustZAD/lunaria-web`, `main` directly, deployed on Railway.

## 2026-06-30 — cream "v2" rebuild (decision record)

The first cut (dark IDE theme + bottom chat dock + non-functional asset/upload + fake buttons) was rejected by the owner as not product-grade. Full frontend rebuild, owner bar = "可以上线运营的 C 端产品". Landed on `main`.

**Stack / aesthetic.** Reuses the IDE's stack — **Radix UI + lucide + CSS-variable tokens (no Tailwind)** — but ships a **cream light theme** (`src/ui/theme-cream.css`: warm-cream surfaces, espresso ink, dusty-rose CTA, `Fraunces` serif), built as a coherent design system (`src/ui/`, ~18 primitives + `DESIGN.md`) verified visually before fan-out. Bundles through the existing esbuild SPA pipeline (CSS inlined).

**UX (Manus-style two-phase).** No script → full-screen onboarding chat (`OnboardingView`, opt-in "load example" so guest mode is usable without the gateway). Script exists → `WorkspaceShell`: 编辑/画布/素材/预览 tabs with the **agent as a persistent right sidebar (not a bottom dock)**. Agent runs on `pi-agent-core` over the IDE gateway. cf. [[concepts/lunaverse-ide-ai-integration]].

## 2026-07-01 — feature completion (4 gaps closed)

The v2 rebuild was functional-but-partial; the owner flagged four gaps, all now closed + browser-verified (472 tests green):

### Image generation — REAL, via login token (corrects an earlier wrong note)
Earlier this page claimed "image-gen must use a separate `MOB_AI_KEY` + assetctl binary" — **wrong**; that's only the local fallback. Truth is the IDE's **remote gateway mode**: `POST {gateway}/api/ide/tools/generate-image-gpt` with `Authorization: Bearer <user login token>` (same token as chat; the gateway holds the provider key). **Any funded account with the `asset:generate` entitlement generates — no provider key needed.** `lunaria-server` now makes this the PRIMARY path (`image/gateway-image.ts`, a faithful TS port of assetctl `mobai.go`/`gpt.go`: async submit → poll `taskId` 60×@5s → extract `imageUrl`/`url`/`result` → download bytes; 11 mock tests — protocol can't be live-tested without a real token, so correctness rides on mirroring the reference). assetctl + `MOB_AI_KEY` demoted to optional local fallback. `GET /api/capabilities.imageGen` is **session-aware** (real token → true, guest → false → honest "登录后可 AI 生成", no dead button).

### Style system (风格选择 + preset prompts)
`image/styles.ts` ports IDE `tools/second-chorus-pipeline/style/styles.json`: 4 families (Arcane / Kyoto_Animation / Webtoon_01 / YA_Impasto) × character/scene variants, verbatim prompt templates + reference_urls. `renderAssetPrompt({family,kind,userPrompt})` injects the user prompt into the template `{{placeholder}}`, appends the chromakey neutral-plate contract for character kinds, normalizes model → `image-gpt`, aspect 9:16 char / 1:1 scene. `GET /api/styles` feeds a family-card picker in the generate dialog. cf. [[concepts/style-langfuse-migration]].

### Directly-editable studio cards
EditorView card mode is now **editable** (was read-only). Each leaf beat renders inline field editors; an edit re-emits only that one source line (`ls/emit-block.ts`) and splices it back at `block.line` preserving indent — compound-block bodies untouched (a **lossless round-trip the IDE's own choice editor lacks** — it drops check/nested content).

### Two-level canvas (剧情图 → 分镜图)
CanvasView: Level 1 scene graph; **double-click a scene → Level 2 per-step 分镜** (`ls/build-step-graph.ts`, built from the locally-compiled episode — lsc runs local, no gateway cost). Steps chain top-down; `@choice` fans out options; a brave option's D20 `check` becomes a dice node 「D20 · CHA ≥ 12」 with 成功/失败 branches; `@if` splits 满足/否则. **Gotcha:** react-flow 12's `onNodeDoubleClick` didn't fire here — detect the double-click manually on `onNodeClick` (same node twice within 350ms) + `zoomOnDoubleClick={false}`.

## Asset mapping + canonical `--assets` gotcha

Web symbols (`@bg set X`, `&char look`, `@cg X`) are parsed (`parseSceneSymbols`) and **bound** to uploaded/generated assets via a per-episode `AssetMapping` (`{backgrounds:[{symbol,assetId}], characters:[{id,looks:[{symbol,assetId}]}], cg:[…]}`), persisted server-side with a coverage panel.

**Gotcha (cost an E2E cycle):** `lsc compile --assets` does **NOT** accept a `{symbol,path}` array. Canonical schema (verified via `lsc decompile` + IDE `project.ts`) is `{ base_url, assets: { bg, characters, music, sfx, cg, minigames } }` — **objects keyed by name**, char keys lowercase. Server emits that with **assetId values under an `asset://` base_url sentinel**; compiled steps carry `url:"asset:///<id>"`, and the **web client rewrites those to authed object URLs** before the player renders (assets are bearer-protected). Same canonical family as [[concepts/assets-produce-ide-workspace-contract]].

## Auth / deploy

Login = IDE gateway `app.moonshort.ai` (`/api/auth/login` → token; the login token **is** the gateway key for both chat AND image-gen). Guest mode (`token=dev`) exercises all non-AI paths; AI returns a graceful 401. Env vars + enabling generation: repo `DEPLOY.md`. Workspace desktop-first; onboarding/login responsive.
