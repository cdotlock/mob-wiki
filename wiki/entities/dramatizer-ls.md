---
title: Dramatizer-LS
tags: [dramatizer, ls, assets, skills, partially-deprecated]
sources: []
created: 2026-05-03
updated: 2026-05-30
---

> **⚠️ 2026-06-05 修正 — assets-produce 已废弃，下面这条迁移说法作废。** novel→`.ls` 的 authoring skills（novel-evaluator / character-architect / bible-reviewer / entity-planner / planner-reviewer / entity-normalizer / episode-writer / episode-writer-reviewer 等）**权威副本现在在 [[entities/lunaverse-ide]] 仓库的 `agents/adaptation/skills/<skill>/SKILL.md`**（已实地确认为完整 live skill，非归档桩），**IDE 是当前唯一标准**。本页下方所有"迁到 / 权威在 assets-produce"叙述（2026-05-19 写入）均已过期、待整体校订。
>
> ~~（历史记录，已作废）2026-05-19 partial deprecation — upstream authoring 10 skills 整体迁到 [[entities/assets-produce]]~~。novel → `.ls` 编剧前半（novel-evaluator / character-architect / bible-reviewer / entity-planner / planner-reviewer / entity-normalizer / entity-rename / rename-reviewer / episode-writer / episode-writer-reviewer / arc-reviewer）已 verbatim 迁到 `cdotlock/assets-produce` 的 `knowledge/novel-to-ls/<skill>/SKILL.md`，由那边的 `novel_to_ls` orchestration skill + `ls-validate` atomic tool 驱动，是唯一权威。每个被迁的 `SKILL.md` 顶部都加了 deprecation banner 警告"don't edit here — changes will not propagate"。本仓库这 10 个 skill 副本**保留作历史归档**。
>
> **仍在本仓维护**：downstream asset pipeline（`asset-prompt-generator` + `asset-renderer` + `asset-reviewer` + cg / outfit / wardrobe canonicalization 全套）+ `dramatizer/` 配套（pipeline / cg config / music normalizer / stage assets）+ NRBI 真实项目工作目录（`lunascripts/no-rules-in-bad-ideas/` 等）。
>
> 迁移设计 spec：assets-produce `docs/superpowers/specs/2026-05-19-upstream-authoring-migration-design.md`（master-spec §15 r1.16）。

Dramatizer-LS 是 novels-to-Lunascript 工具链：把长篇言情小说改编成 Lunaverse-ready LS 剧本 + 角色 bible + 路线规划 + 素材 prompt + 渲染好的视觉小说素材。它和老的 Go [[entities/dramatizer]] service 不同：Dramatizer-LS 是 Claude Code skill + artifact 工作流，Dramatizer 是更早的 Go pipeline + 集成二进制。

**2026-05-19 后实际角色压缩**：编剧前半（评估 / 角色 / 路线 / 集数规划 / 编剧 / 审稿）走 assets-produce；本仓只跑素材渲染下半（asset prompt / 渲染 / 审图 / cg pipeline / wardrobe + outfit + sprite canonical / music normalizer）+ NRBI 实际生产工程文件夹。

## Repository Identity

| Field | Value |
|---|---|
| Repository path | `/Users/Clock/lunaverse/dramatizer-ls` |
| Primary branch | `main` |
| Remote | `origin/main` |
| Product name | Novels to Lunascript |
| Main entry docs | `README.md`, `SKILLS-GUIDE.md`, `CLAUDE.md` |
| Output format | LS scripts plus asset task JSON |
| Example project | `lunascripts/no-rules-in-bad-ideas/` |
| Remote MCP dependency | `style-prompts` SSE MCP at `https://broti.mob-ai.cn/mcp-style/sse` |

The repository contains a full adaptation pipeline: evaluate a source novel, rebuild game-suitable characters, plan episode and route structure, normalize entity IDs, write LS, review each episode, review entire arcs, generate visual asset prompts, render images, and review the resulting images.

## Product Role

The repository fills the gap between raw novels and Lunaverse runtime content. It is not only a script writer. It owns the full pre-runtime production path:

```text
novel text
  -> novel evaluation
  -> character bible
  -> route and episode planning
  -> entity normalization
  -> LS episode writing
  -> episode and arc review
  -> asset prompt generation
  -> image rendering
  -> asset review
  -> Lunaverse app import
```

The target audience is North American women aged 18-24, with romance and otome pacing as the default product assumption. This matters because the skills judge character agency, love-interest differentiation, choice stakes, episode hooks, and visual style against that audience.

## Skill Inventory

The repository historically defined 12 major skills. **2026-05-19 起 11 个被标 deprecated — 编剧前半（authoring）全迁到 [[entities/assets-produce]]**：

| Skill | Status | Main output | Now lives in |
|---|---|---|---|
| `novel-evaluator` | ⚠️ DEPRECATED | GO/NO-GO report. | assets-produce `knowledge/novel-to-ls/novel-evaluator/SKILL.md` |
| `character-architect` | ⚠️ DEPRECATED | Character Bible Set. | assets-produce `knowledge/novel-to-ls/character-architect/SKILL.md` |
| `bible-reviewer` | ⚠️ DEPRECATED | PASS/CONDITIONAL/FAIL report. | assets-produce 同上路径 |
| `entity-planner` | ⚠️ DEPRECATED | Episode and route planning document. | assets-produce 同上路径 |
| `planner-reviewer` | ⚠️ DEPRECATED | Planner review report. | assets-produce 同上路径 |
| `entity-normalizer` | ⚠️ DEPRECATED | `characters.json`, `locations.json`, `alias_map.json`. | assets-produce 同上路径 |
| `entity-rename` | ⚠️ DEPRECATED | `rename_map.json`, batch-renamed scripts. | assets-produce 同上路径 |
| `rename-reviewer` | ⚠️ DEPRECATED | `apply_report.md`. | assets-produce 同上路径 |
| `episode-writer` | ⚠️ DEPRECATED | `ep_N_final.md`. | assets-produce 同上路径 |
| `episode-writer-reviewer` | ⚠️ DEPRECATED | Episode review report. | assets-produce 同上路径 |
| `arc-reviewer` | ⚠️ DEPRECATED | Arc prescriptions and revised scripts. | assets-produce 同上路径 |
| `asset-prompt-generator` | ✅ Active | `tasks_output.json`, wardrobe/canonicalization artifacts. | dramatizer-ls `skills/asset-prompt-generator/` |
| `asset-renderer` | ✅ Active (本仓壳，实跑走 backend) | PNG assets. | dramatizer-ls `skills/asset-renderer/`，实际渲染走 backend `generate-upscale-matting/`（2026-05-07 切换） |
| `asset-reviewer` | ✅ Active | `img_review.md`. | dramatizer-ls `skills/asset-reviewer/` |

迁后跨 repo 的实际工作流：

```
assets-produce (novel_to_ls orchestration)
  → 跑 novel-evaluator → character-architect → bible-reviewer
  → entity-planner / planner-reviewer / entity-normalizer / entity-rename / rename-reviewer
  → episode-writer / episode-writer-reviewer / arc-reviewer
  → 产出 ep_N_final.md + characters.json + locations.json + bible.md
       │
       ▼ artifact handoff
dramatizer-ls (downstream)
  → asset-prompt-generator（含 wardrobe canonicalizer + sprite C' + outfit anchor renderer）
  → asset-renderer（壳）→ backend `generate-upscale-matting/` 实跑
  → asset-reviewer + cg-renderer + music-normalizer
       │
       ▼
backend assets/<book-slug>/ → LS engine 消费
```

All reviewer steps are intentionally separated from writer steps. The repository treats self-review as a failure mode; reviewer agents are supposed to cold-read artifacts and report concrete defects before the main worker edits.

## LS Writing Rules

Dramatizer-LS writes Lunascripts, which is documented in [[entities/lunascripts]] and [[concepts/ls-format]]. The `episode-writer` skill contains a local `ls-spec.md` copy for authoring, but upstream source of truth remains the Lunascripts repository.

Important current writing rules include:

| Rule | Reason |
|---|---|
| NARRATOR lines addressing the main character must use uppercase `YOU`, `YOUR`, or `YOURS`. | The target product uses second-person player embodiment, not third-person prose about the protagonist. |
| Other female characters may still use she/her when the subject is explicit. | The validator tracks named subjects to avoid overcorrecting non-MC references. |
| `@option` labels must be short: 80 English characters or 60 visible-width Chinese columns. | Full dialogue belongs inside the option body, not in the choice label UI. |
| LS output must remain compiler-valid. | Runtime only consumes compiled EpisodeJSON. |
| Writer output should score at least 9.0 before handoff. | The workflow optimizes for production quality, not rough drafts. |

`skills/episode-writer/check_narrator_pov.py` enforces the NARRATOR and option-label rules. It can detect-only or auto-fix MC pronoun references while leaving option-label violations as manual fixes.

## Asset Pipeline

The asset pipeline converts normalized character and scene identity into renderable tasks.

| Stage | Artifact | Purpose |
|---|---|---|
| Entity normalization | `characters.json`, `locations.json`, alias maps | Gives scripts and visual prompts stable IDs. |
| Asset prompt generation | `tasks_output.json` | One task per character look or scene render. |
| Clothing consistency check | Scene outfit truth tables | Ensures wardrobe does not drift across beats. |
| Sprite canonicalization | `look_alias_map.json`, `dedup_tasks_output.json` | Merges visually equivalent sprite tasks before rendering. |
| Rendering | PNG assets | Produces source images for runtime and later video work. |
| Review | `img_review.md` | Lists failed renders and required prompt changes. |

The remote `style-prompts` MCP stores shared prompt templates in a central service. Agents configure it once in Claude Code with an API key and then call the MCP from `asset-prompt-generator`. This keeps visual style templates versioned and shared across the team rather than duplicated in every local skill file.

## Sprite Canonical C Prime

The biggest 2026-04-29 to 2026-05-01 technical change is Sprite Canonical, also called C'. It addresses sprite explosion during asset generation.

The motivating data from `no-rules-in-bad-ideas` was:

| Metric | Value |
|---|---:|
| LS files in ep10-22 | 48 |
| Initial `(char, look_name)` records | 3,608+ |
| Selena share | 46% |
| One-off looks | 72% |
| Estimated render budget before dedup | about $725 |

The root cause is that `look_name` had been overloaded with identity, outfit, pose, gesture, and emotion. Many names differed only by adjectives that the image model cannot render as meaningfully distinct images.

C' merges sprite tasks by:

```text
same character
AND same outfit_id
AND same geometry_signature
```

The geometry signature started as a 5-tuple and evolved to a 7-tuple:

| Field | Meaning |
|---|---|
| `head` | Chin/head direction such as up, down, tilted, neutral. |
| `hands` | Hand placement such as on hips, by side, crossed, to face, extended. |
| `weight` | Body weight distribution. |
| `gaze` | Eye target such as camera, floor, another character, distant. |
| `torso` | Frontal, three-quarter, profile, back. |
| `face` | Mouth/face state such as neutral, smile, grin, frown, parted lips. |
| `eyes` | Open, closed, half-open, wide, squint, or other. |

Emotion adjectives like decisive, quiet, caught, held, or acknowledging do not enter the merge key unless they materially change geometry.

## Wardrobe Canonicalization

C' exposed a second problem: outfit text drift. Upstream prompt generators may describe the same outfit differently across episodes, such as "casual daily outfit", "home loungewear", and "casual home outfit with bracelet". If these text fragments become raw outfit IDs, otherwise identical sprites never merge.

The current canonicalizer therefore has a wardrobe layer:

1. Load canonical wardrobe entries from character bible files when available.
2. Build or load a `wardrobe_map.json` that maps paraphrased outfit fragments to stable wardrobe IDs.
3. Derive `outfit_id` by trying truth-table items, then wardrobe map, then outfit text, and only then falling back to a slug.
4. Use `(char, outfit_id, geometry_signature)` as the final grouping key.

The 2026-05-01 Phase D2 report recorded a real bug in this fall-through order. Truth-table items were conceptual labels, while wardrobe map keys were render-text labels. The old implementation joined truth-table items and, if there was no direct wardrobe hit, immediately slugged them. That skipped the outfit-text path where the wardrobe map would have matched. After fixing fall-through, fallback groups dropped to zero for the demo run.

## Phase D2 Results

After writing fallback wardrobe IDs back into bible files and rerunning canonicalization:

| Metric | Before D2 | After D2 | Change |
|---|---:|---:|---:|
| Records to canonical groups | 4,172 -> 2,163 | 4,172 -> 1,955 | -208 groups |
| Dedup ratio | 48.2% | 53.1% | +4.9 points |
| Sprite tasks using bible IDs | 84.1% | 100% | +15.9 points |
| Fallback ID groups | 66 | 0 | -66 |
| Bible outfit entries | 96 | 103 | +7 |

The result saved an estimated additional 208 sprite renders for the demo book. The team did not render the 1,955 final sprites automatically because rendering would incur real cost.

## Recent Git History

The 2026-04-27 to 2026-05-01 history added:

| Area | Changes |
|---|---|
| Chroma key cleanup | Added and documented `green_spill_clear.py` for bright green halo cleanup. |
| NRBI scripts | Added English/Chinese translations and E9-E22 LS finals for routes and endings. |
| Clothing checks | Added `check_clothing_consistency.py` to flag prompts missing scene-specific outfit details. |
| Sprite canonicalization | Added design, plan, dataclasses, alias map building, LLM geometry extraction, wardrobe IDs, and dedup output generation. |
| D2 wardrobe contract | Added canonical wardrobe entries, fixed supporting-cast Chinese IDs, strengthened LLM wardrobe prompt, and fixed derive fall-through. |
| Writer validator | Enforced second-person NARRATOR and option label length. |
| Prompt generator | Added canonical wardrobe contract per character bible. |

## Relationship To Other Pages

Dramatizer-LS is upstream of [[entities/lunaverse-backend]] and [[entities/lunaverse-client]] because it produces the content those systems run. It is also a reference source for [[concepts/dreaming-universe]], whose writer specialists borrow LS writing and review ideas from this repository.

It is not a replacement for [[entities/lunascripts]]. Lunascripts is the compiler and format; Dramatizer-LS is an authoring and asset-production workflow that writes that format.

## Sources

This page was reconstructed from local repository files and history under `/Users/Clock/lunaverse/dramatizer-ls`, especially:

- `README.md`
- `docs/superpowers/specs/2026-04-29-sprite-canonical-c-prime-design.md`
- `docs/superpowers/plans/2026-04-29-sprite-canonical-c-prime.md`
- `docs/superpowers/reports/2026-05-01-phase-d2-bible-fallback-writeback.md`
- `skills/asset-prompt-generator/look_canonicalizer.py`
- `skills/episode-writer/check_narrator_pov.py`
- Git history from 2026-04-27 through 2026-05-01
