---
title: Dramatizer-MSS
tags: [dramatizer, mss, assets, skills]
sources: []
created: 2026-05-03
updated: 2026-05-03
---

Dramatizer-MSS is the novels-to-Moonscript toolchain used to adapt long-form romance novels into Moonshort-ready MSS scripts, character bibles, route plans, asset prompts, and rendered visual-novel assets. It is separate from the older Go [[entities/dramatizer]] service: Dramatizer-MSS is a Claude Code skill-and-artifact workflow, while Dramatizer is the earlier Go pipeline and integration binary.

## Repository Identity

| Field | Value |
|---|---|
| Repository path | `/Users/Clock/moonshort/dramatizer-mss` |
| Primary branch | `main` |
| Remote | `origin/main` |
| Product name | Novels to Moonscript |
| Main entry docs | `README.md`, `SKILLS-GUIDE.md`, `CLAUDE.md` |
| Output format | MSS scripts plus asset task JSON |
| Example project | `moonscripts/no-rules-in-bad-ideas/` |
| Remote MCP dependency | `style-prompts` SSE MCP at `https://broti.mob-ai.cn/mcp-style/sse` |

The repository contains a full adaptation pipeline: evaluate a source novel, rebuild game-suitable characters, plan episode and route structure, normalize entity IDs, write MSS, review each episode, review entire arcs, generate visual asset prompts, render images, and review the resulting images.

## Product Role

The repository fills the gap between raw novels and Moonshort runtime content. It is not only a script writer. It owns the full pre-runtime production path:

```text
novel text
  -> novel evaluation
  -> character bible
  -> route and episode planning
  -> entity normalization
  -> MSS episode writing
  -> episode and arc review
  -> asset prompt generation
  -> image rendering
  -> asset review
  -> Moonshort app import
```

The target audience is North American women aged 18-24, with romance and otome pacing as the default product assumption. This matters because the skills judge character agency, love-interest differentiation, choice stakes, episode hooks, and visual style against that audience.

## Skill Inventory

The repository defines 12 major skills:

| Skill | Purpose | Main output |
|---|---|---|
| `novel-evaluator` | Score a source novel across adaptation dimensions such as MC agency, LI depth, zero-explanation genre fit, choice potential, fantasy type, and natural branches. | GO/NO-GO report. |
| `character-architect` | Rebuild novel characters into game characters with personality, wounds, secrets, affection rules, signal hooks, and route conditions. | Character Bible Set. |
| `bible-reviewer` | Verify character bible details against the original novel and check LI differentiation. | PASS/CONDITIONAL/FAIL report. |
| `entity-planner` | Plan public route and LI-specific routes, episode counts, signals, affection changes, and branch structure. | Episode and route planning document. |
| `planner-reviewer` | Independently simulate each LI route and run cross-route consistency checks. | Planner review report. |
| `entity-normalizer` | Normalize character and location names into stable IDs used by scripts and assets. | `characters.json`, `locations.json`, `alias_map.json`. |
| `episode-writer` | Write MSS episodes from bible, plan, and normalized IDs. | `ep_N_final.md`. |
| `episode-writer-reviewer` | Simulate the target player, check bible/plan/MSS adherence, and score the episode. | Episode review report. |
| `arc-reviewer` | Review a complete arc using narrative inventories for facts, promises, signals, choices, continuity, and LI agency. | Arc prescriptions and revised scripts. |
| `asset-prompt-generator` | Turn character and location descriptions into image-generation prompts and task JSON. | `tasks_output.json`, wardrobe/canonicalization artifacts. |
| `asset-renderer` | Render character sprites and scenes through image generation and post-processing. | PNG assets. |
| `asset-reviewer` | Review rendered images against prompts and create rework instructions. | `img_review.md`. |

All reviewer steps are intentionally separated from writer steps. The repository treats self-review as a failure mode; reviewer agents are supposed to cold-read artifacts and report concrete defects before the main worker edits.

## MSS Writing Rules

Dramatizer-MSS writes MoonShort Script, which is documented in [[entities/moonshort-script]] and [[concepts/mss-format]]. The `episode-writer` skill contains a local `mss-spec.md` copy for authoring, but upstream source of truth remains the Moonshort Script repository.

Important current writing rules include:

| Rule | Reason |
|---|---|
| NARRATOR lines addressing the main character must use uppercase `YOU`, `YOUR`, or `YOURS`. | The target product uses second-person player embodiment, not third-person prose about the protagonist. |
| Other female characters may still use she/her when the subject is explicit. | The validator tracks named subjects to avoid overcorrecting non-MC references. |
| `@option` labels must be short: 80 English characters or 60 visible-width Chinese columns. | Full dialogue belongs inside the option body, not in the choice label UI. |
| MSS output must remain compiler-valid. | Runtime only consumes compiled EpisodeJSON. |
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
| MSS files in ep10-22 | 48 |
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
| NRBI scripts | Added English/Chinese translations and E9-E22 MSS finals for routes and endings. |
| Clothing checks | Added `check_clothing_consistency.py` to flag prompts missing scene-specific outfit details. |
| Sprite canonicalization | Added design, plan, dataclasses, alias map building, LLM geometry extraction, wardrobe IDs, and dedup output generation. |
| D2 wardrobe contract | Added canonical wardrobe entries, fixed supporting-cast Chinese IDs, strengthened LLM wardrobe prompt, and fixed derive fall-through. |
| Writer validator | Enforced second-person NARRATOR and option label length. |
| Prompt generator | Added canonical wardrobe contract per character bible. |

## Relationship To Other Pages

Dramatizer-MSS is upstream of [[entities/moonshort-backend]] and [[entities/moonshort-client]] because it produces the content those systems run. It is also a reference source for [[concepts/dreaming-universe]], whose writer specialists borrow MSS writing and review ideas from this repository.

It is not a replacement for [[entities/moonshort-script]]. Moonshort Script is the compiler and format; Dramatizer-MSS is an authoring and asset-production workflow that writes that format.

## Sources

This page was reconstructed from local repository files and history under `/Users/Clock/moonshort/dramatizer-mss`, especially:

- `README.md`
- `docs/superpowers/specs/2026-04-29-sprite-canonical-c-prime-design.md`
- `docs/superpowers/plans/2026-04-29-sprite-canonical-c-prime.md`
- `docs/superpowers/reports/2026-05-01-phase-d2-bible-fallback-writeback.md`
- `skills/asset-prompt-generator/look_canonicalizer.py`
- `skills/episode-writer/check_narrator_pov.py`
- Git history from 2026-04-27 through 2026-05-01
