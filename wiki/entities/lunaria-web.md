---
title: lunaria-web
updated: 2026-06-30
---

# lunaria-web

Consumer-facing (C-end) web tool to author interactive otome/visual-novel **Lunascript (`.ls`)** with an AI agent — a stripped-down, browser-native cousin of [[entities/lunaverse-ide]]. pnpm monorepo: `lunaria-web` (React 18 SPA), `lunaria-server` (Node backend), `shared`, `player-core`. Repo `AugustZAD/lunaria-web`, deployed on Railway.

## 2026-06-30 — cream "v2" rebuild (decision record)

The first cut (dark IDE theme + bottom chat dock + non-functional asset/upload + fake buttons) was rejected by the owner as not product-grade. Full frontend rebuild, owner bar = "可以上线运营的 C 端产品". Landed on `main` (`8e8d6b6..d427220`, 8 commits), 415 tests green, E2E-verified in guest mode.

**Stack / aesthetic.** Reuses the IDE's stack — **Radix UI + lucide + CSS-variable tokens (no Tailwind)** — but ships a **cream light theme** (`src/ui/theme-cream.css`: warm-cream surfaces, espresso ink, dusty-rose CTA, `Fraunces` serif), built as a coherent design system (`src/ui/`, ~18 primitives + `DESIGN.md`) verified visually before fan-out. Bundles through the existing esbuild SPA pipeline (CSS inlined).

**UX (Manus-style two-phase).** No script → full-screen onboarding chat (`OnboardingView`, with an opt-in "load example" so guest mode is usable without the gateway). Script exists → `WorkspaceShell`: 编辑/画布/素材/预览 tabs with the **agent as a persistent right sidebar (not a bottom dock)**.

**Agent.** Generation runs on `pi-agent-core` (core only) over the IDE gateway; behavior-identical to the prior hand-rolled loop. cf. [[concepts/lunaverse-ide-ai-integration]].

## Asset mapping (the headline feature) + key gotcha

Web symbols (`@bg set X`, `&char look`, `@cg X`) are parsed (`parseSceneSymbols`) and **bound** to uploaded/generated assets via a per-episode `AssetMapping` (web shape: `{backgrounds:[{symbol,assetId}], characters:[{id,looks:[{symbol,assetId}]}], cg:[…]}`), persisted server-side and shown with a coverage panel.

**Gotcha (cost us an E2E cycle):** `lsc compile --assets` does **NOT** accept a `{symbol,path}` array. The canonical schema (verified via `lsc decompile` + the IDE's `project.ts` template) is `{ base_url, assets: { bg, characters, music, sfx, cg, minigames } }` — **objects keyed by name**, char keys lowercase. The server translates the web mapping into that schema with **assetId values under an `asset://` base_url sentinel**; compiled steps then carry `url:"asset:///<id>"`, and the **web client rewrites those to authed object URLs** before the player renders (project assets are bearer-protected, so the browser can't load them by raw URL). Same canonical mapping family as [[concepts/assets-produce-ide-workspace-contract]].

## Image generation + capabilities

Image-gen is **not** a chat-gateway call. It shells out to the `assetctl` binary (`generate-image-gpt`, cf. [[concepts/assetctl-integration-contract]]) with a separate `MOB_AI_KEY`; the IDE gates it behind an `asset:generate` entitlement web accounts may lack. `lunaria-server` exposes `GET /api/capabilities → {imageGen, compiler}`; `imageGen` is true only when `assetctl` resolves (`LUNARIA_ASSETCTL_BIN`) **and** `MOB_AI_KEY` is set. The asset UI shows "生成" only then — otherwise upload-only with an honest note (no fake buttons). Heavy post-processing (matting/upscale, [[concepts/comfyui-modal-deploy]]) is intentionally not ported.

## Auth / deploy

Login = IDE gateway `app.moonshort.ai` (`/api/auth/login` → token; the login token **is** the gateway key for AI). Guest mode (`token=dev`) exercises all non-AI paths; AI returns a graceful 401. Deploy env vars + how to enable generation: see repo `DEPLOY.md`. Workspace is desktop-first; onboarding/login are responsive.
