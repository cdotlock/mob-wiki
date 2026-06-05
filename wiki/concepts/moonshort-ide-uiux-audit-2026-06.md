---
title: Moonshort IDE UI/UX Audit + Fix Log (2026-06)
---

## TL;DR

Full UI/UX audit of Moonshort IDE's 4 custom webviews (Studio block editor, Workshop asset console, Preview stage + voice casting, Welcome first-run). **33 findings → 32 fixed, committed to `cdotlock/moonshort-ide` `main` (tip `2b69c27`), and hot-patched into the installed `.app`. The 1 remaining (M10/L3) is gated on rebuilding the bundled cline VSIX (= full `fork/build.mjs`).** Verification at each step: typecheck clean · node suite 362/363 (1 pre-existing fail) · workshop component tests 889/889.

## Scope & method

- Audited the 4 product webviews only (the VS Code shell is inherited / out of scope). Personas: **Writer** (Studio→Preview), **Producer** (Workshop), **New user** (Welcome).
- Pipeline: 5 live screenshots + full source read + an 8-agent verify/critique workflow + 3 background fix-agents (workshop bulk, workshop tokens/i18n, studio).
- **Headline design-system finding (fixed as M12):** the editor-vs-Material visual split is *intentional* (the shared `packages/shared/src/stage/tokens.css` defines both an editor palette and an `--md-*` Material palette). The only defect was Workshop's `theme.ts` `C` object **hardcoding** the `--md-*` values instead of consuming them — now re-pointed to `var(--md-*)` (28/28 byte-identical, zero visual change).

### Environment issues surfaced (pre-existing, not introduced)

- **computer-use pixel-clicks were coordinate-broken** (every click hit-tested to the Dock) → drove the IDE by keyboard; ProductionExplorer + Welcome audited from source.
- **`@material/web` and `vitest` declared but unmaterialized** in `node_modules` → `pnpm install --frozen-lockfile` fixed both with **no lockfile change**.
- **1 pre-existing failing node test:** `workshop-agent-config` "missing-key error names User Settings…" (stale copy) — left untouched (baseline = 362/1).

## Fixed (32) — committed + pushed + deployed

**High (9):** H1 `@char look <sprite>` parser misparse → reserved-pose guard (+test) · H2 `--text-muted`/`C.textFaint` WCAG-AA contrast (→0.62) · H3 first-run Welcome now opens · H4 Preview Space/I scoped to player + buttons exempt · H5 Delete/Backspace deletes beats · H6 Welcome "Create" opens the new episode in F Studio · H7 chip dropdowns wrapped in listbox + activedescendant · H8 arrow-key caret nav between beats (roving tabindex, ⌥↑↓-move + textarea-edit guards verified) · H9 ProductionExplorer fully i18n'd (470 EN/ZH parity).

**Medium (13):** M1 player empty-state (mode-aware) · M2 release scan ProgressIndicator · M3 "T8"/"T13" codenames removed · M4 style-menu Escape/outside-click dismiss · M5 grid empty states (GridEmpty) · M6 breadcrumb keyboard/SR a11y · M7 voice filter button-group + aria-pressed · M8 disabled-action reasons · M9 voice live regions · M11 Release Center i18n · M12 Workshop consumes shared `--md-*` tokens (28/28 byte-identical) · M13 music 'play' option removed (track + stop toggle) · M14 onboarding focus trap · M15 preview responsive narrow layout.

**Low (10):** L1 status-bar action feedback (aria-live) · L2 「音色」→ "Tone" · L4 onboarding dismiss de-emphasized · L5 disabled-button affordance · L6 conditional logout · L7 required title + placeholder samples · L8 IfBlock whole-header toggle · L9 ~31 ad-hoc hex → tokens.

**Plus (beyond the original 33):** `production-explorer/DetailPanel.tsx` fully localized (it had been scoped out of H9; finished in the follow-up — 65 new keys, EN/ZH 528/528 parity).

## Remaining (1) — gated on the full build

- **M10 / L3 — command palette polluted by bundled cline commands** (8× Jupyter/dev commands; "Focus on  View" double space from an empty webview-view `name`). Spec: add a `contributes.menus.commandPalette` `[{ "command": "<id>", "when": "false" }]` block to `fork/cline-custom/moonshort.patch` for the 8 commands + set the view `name`. **Gated: only takes effect after rebuilding the cline VSIX, which requires the full `fork/build.mjs` (project rule: no full build without explicit go-ahead). Do the patch edit + build in one pass so it's immediately verifiable.**

## Verification (final)

- `pnpm typecheck` (whole monorepo): clean · root node suite: **362/363** (the 1 fail is pre-existing) · workshop vitest: **71 files / 889 tests pass** · all 8 packages build Done.
- 4 changed webviews hot-patched into `/Applications/Moonshort IDE.app` (byte-verified with `cmp`) and the app restarted.
- Pushed to `cdotlock/moonshort-ide` `main` @ `2b69c27` (~20 atomic commits; the workshop i18n/token commits necessarily group findings that share `i18n.ts` / `tokens.css`).

_Audit + fix run: 2026-06-05 → 06._
