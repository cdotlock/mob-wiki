---
title: Video Agent Claude Wangbo
tags: [video, agent, seedance, oss, skill]
sources: [raw/2026-05-11-assets-produce-local-videoctl-cleanup.md]
created: 2026-05-03
updated: 2026-05-11
---

Video Agent Claude Wangbo is the repository for the short-drama shot prompt production workflow used to turn Lunaverse episode scripts into Seedance-ready video generation prompts. It is not a general Agent-Forge replacement; it is a focused Claude Code skill package plus a `works/` workspace convention, OSS validation scripts, gateway payload tooling, and an ablation record showing why the new skill package replaced the legacy workflow.

## Repository Identity

| Field | Value |
|---|---|
| Repository path | `/Users/Clock/video-agent-claude-wangbo` |
| Primary branch | `main` |
| Remote | `origin/main` |
| Current tag | `v2` |
| Main product surface | `agent-skills/video-episode-generation/SKILL.md` |
| Active work root | `works/` |
| Active example work | `works/silver-moon-manor/` |
| Internal video gateway | `https://agent.mob-ai.cn/api/external/video/generate` |
| Internal upload endpoint | `https://agent.mob-ai.cn/api/external/video/oss/upload` |

The repository was imported on 2026-04-29 and was heavily refactored on 2026-05-02. The important post-refactor convention is that all active production artifacts live under `works/{novel_id}/`, while completed works can later move to `archive/{novel_id}/` after explicit confirmation.

## Product Role

The repository supports one user-facing workflow: given an episode JSON script, generate one or more high-quality video prompts, validate all media references, call the internal Seedance gateway, and retain the resulting prompt and URL sidecars for audit and later continuation.

The workflow is designed for interactive short-drama production, where one episode is split into multiple shots. Each shot prompt must preserve story continuity, physical space, character identity, wardrobe, emotion, camera direction, sound cues, and forbidden visual errors. The skill is intentionally stricter than a generic prompt-writing assistant because video generation failures are expensive and hard to diagnose after the fact.

## Directory Model

The current directory model is:

| Path | Purpose |
|---|---|
| `agent-skills/video-episode-generation/` | Claude Code skill package. This is the entry point for prompt generation and review. |
| `agent-skills/video-episode-generation/references/` | Required reading files loaded at specific workflow steps. |
| `agent-skills/video-episode-generation/scripts/` | Utility scripts for OSS upload, URL validation, payload construction, video download, and frame extraction. |
| `works/{novel_id}/scripts/` | Episode JSON source scripts. |
| `works/{novel_id}/assets/` | Character portraits and scene images used as source references. |
| `works/{novel_id}/ref-frames/` | Episode-specific video or image reference frames. |
| `works/{novel_id}/episodes/ep_{N}/shots/` | Shot prompt output directories. |
| `works/{novel_id}/episodes/ep_{N}/end-frames/` | End-frame and spatial-frame outputs for shot continuation. |
| `archive/{novel_id}/` | Completed works, only after user confirmation. |
| `ablation/` | Legacy-vs-new skill experiment inputs and report. |

Git policy for this repository is that generated prompt `.md` files and URL sidecars should be committed, while image and video binaries should not be committed unless the repository intentionally tracks a small reference asset.

## Skill Package Architecture

`agent-skills/video-episode-generation/SKILL.md` is the operational contract for agents. Its main rules are:

| Rule area | Requirement |
|---|---|
| Source authority | Read the full episode JSON before writing any shot prompt. Do not rely on pasted excerpts or memory. |
| Reference loading | Each workflow step has required reference files. For example, character references must come from `references/character-dna.md`; format checks must consult `references/authority-prompt-template.md`. |
| Prompt format | Prompts follow a nine-section structure: style declaration, character uniqueness, image-reference explanation, narrative brief, timeline, shot breakdown, sound, prohibitions, and material list. |
| Quality review | A cold reviewer checks the prompt against `references/review-checklist.md`; every group must pass before the main agent calls generation. |
| User confirmation | In the default interactive mode, generation stops after prompt review and waits for human confirmation. |
| Fast mode | The phrase `开启钟文鼎特批危险超速生成模式` is the explicit opt-in for skipping human confirmation, but URL validation remains mandatory. |
| Timeout | Video generation can take up to 1200 seconds. A 120-second timeout is explicitly invalid. |
| Evidence language | Agents must report verified facts such as command output and file paths, not vague claims such as "should be complete". |

The skill separates three roles:

| Role | Responsibility | Hard boundary |
|---|---|---|
| Worker agent | Reads the script and references, then writes `prompt.md`. | Must not call the video generation API. |
| Reviewer agent | Cold-reads the produced prompt and checks the review checklist. | Must not share the main agent's assumptions. |
| Main controller | Reviews worker and reviewer output, validates URLs, calls generation, downloads outputs, and extracts frames. | Owns the only path to video generation. |

## Gateway Contract

All video generation goes through the internal gateway:

```text
POST https://agent.mob-ai.cn/api/external/video/generate
Authorization: Bearer $AGENT_API_KEY
```

The repository keeps storage details behind the server. Local operators configure:

```text
AGENT_API_BASE=https://agent.mob-ai.cn
AGENT_API_KEY=<internal bearer token>
AGENT_UPLOAD_PATH=/api/external/video/oss/upload
AGENT_VIDEO_GENERATE_PATH=/api/external/video/generate
```

The gateway payload builder is `agent-skills/video-episode-generation/scripts/build_gateway_payload.py`. It reads YAML frontmatter and prompt body from `prompt.md` and emits JSON with these fields:

| Field | Source | Meaning |
|---|---|---|
| `action` | fixed | Always `generate`. |
| `prompt` | markdown body | Final Seedance prompt text. |
| `duration` | frontmatter `duration` | Video duration in seconds. |
| `ratio` | frontmatter `ratio`, default `9:16` | Output aspect ratio. |
| `resolution` | frontmatter `resolution`, default `720P` | Output resolution. |
| `sourceImageUrl` | first resolved image | Main image reference. |
| `referenceImageUrls` | remaining images | Additional image references. |
| `sourceVideoUrls` | frontmatter video references | Previous or spatial video references. |
| `continuationTailSeconds` | frontmatter `continuation_tail_seconds` | Tail segment used for continuation. |

The builder refuses local media paths unless a sibling `.url` sidecar resolves them to an OSS URL. It also rejects non-OSS URLs by default. This prevents a common failure mode where a prompt looks complete locally but the gateway cannot read the referenced asset.

## Utility Scripts

| Script | Command shape | Purpose |
|---|---|---|
| `upload_to_oss.py` | `python .../upload_to_oss.py <file...>` | Upload local assets to the internal OSS endpoint and write `<file>.url` sidecars. |
| `validate_urls.py` | `python .../validate_urls.py <prompt.md>` | Resolve all prompt URLs, check reachability, content type, and size before generation. |
| `build_gateway_payload.py` | `python .../build_gateway_payload.py <prompt.md>` | Convert a prompt into gateway JSON without calling the gateway. |
| `download_video.py` | `python .../download_video.py --url <video_url> --out <shot.mp4>` | Download a generated video and write a sidecar URL. |
| `extract_end_frame.py` | `python .../extract_end_frame.py <shot.mp4> <shot_end.png>` | Extract the terminal frame used for temporal continuation. |
| `extract_frame_candidates.py` | `python .../extract_frame_candidates.py <shot.mp4> <dir> --shot-id <id>` | Produce candidate spatial references from a video. |
| `select_spatial_frame.py` | `python .../select_spatial_frame.py <candidate.png> <shot_spatial.png>` | Promote one candidate frame to the spatial reference used by later shots. |

## Prompt Workflow

The standard shot workflow is:

1. Read `works/{novel_id}/scripts/ep_{N}.json`.
2. Locate the exact source position for the shot.
3. Write three frontmatter lines: `shot_function`, `prev_shot_recap`, and `next_shot_setup`.
4. Read character DNA, Seedance lessons, and director playbook references.
5. Enumerate every character physically present in the scene, including silent observers.
6. Select references in this order: spatial reference, temporal continuation frame, character DNA portraits.
7. Write the nine-section prompt.
8. Run cold review against the 27-item checklist.
9. Wait for user confirmation unless fast mode was explicitly enabled.
10. Run `validate_urls.py`.
11. Build payload and call the gateway.
12. Download output, write URL sidecars, and extract end/spatial frames for continuity.

The main reason for this strict sequence is continuity. A visually plausible shot can still be production-wrong if it forgets an observer, changes a character's outfit, reverses the room geometry, or starts from a pose that contradicts the previous shot's terminal frame.

## Ablation Findings

The 2026-05-02 ablation compared the old legacy workflow against the new `SKILL.md` across five EP2 shots, with five runs per group. The report found that the new skill was better on total score, especially nine-section completeness and format stability.

| Dimension | Legacy average | New skill average | Difference |
|---|---:|---:|---:|
| Nine-section completeness | 3.40 | 4.50 | +1.10 |
| Reference accuracy | 2.00 | 1.80 | -0.20 |
| Emotional frontmatter | 3.70 | 3.80 | +0.10 |
| Format fit | 3.10 | 3.80 | +0.70 |
| Four-dimension total | 12.20 | 13.90 | +1.70 |

The negative result on reference accuracy is important. The new skill improved structure but initially used the new `works/` path convention where the ground truth still used legacy local paths. The follow-up commits aligned the repository on `works/`, downgraded the old authority template to format-only, removed `legacy/`, and migrated all references and prompts to the new path convention.

## Recent Git History

The important 2026-05-02 to 2026-05-03 changes are:

| Commit theme | Meaning |
|---|---|
| Skill redesign | The old ad hoc workflow was replaced by `agent-skills/video-episode-generation/` with required references, scripts, and an explicit controller/worker/reviewer model. |
| Ablation experiment | Five cases x five runs x two groups were added, then summarized in `ablation/ABLATION_REPORT.md`. |
| Legacy removal | `legacy/` was removed after the ablation showed the new skill package was the active direction. |
| OSS workflow refinement | Upload, validation, payload building, video download, and frame extraction scripts were added or hardened. |
| `works/` migration | Prompt paths, reference paths, and work products were migrated from legacy directories into `works/{novel_id}/`. |
| Gateway correctness | Payload field names were corrected to match the deployed server: notably `sourceImageUrl` instead of older local assumptions. |

## Relationship To Other Pages

This page complements [[entities/agent-forge]]. Agent-Forge is the broader video production platform and MCP/API surface. Video Agent Claude Wangbo is a narrower, file-based Claude Code production skill focused on shot-level prompt authoring and controlled Seedance gateway calls.

As of 2026-05-11, [[entities/assets-produce]] is the active consolidation target for this workflow. Assets-Produce absorbed the useful shot-prompt lessons into `knowledge/novel-to-video/`, replaced shell-driven prompt workflow checks with the local opencode `videoctl` tool, and removed its copied `video-agent-test/agent-skills/` tree from the active repository. Video Agent Claude Wangbo remains the historical source of the prompt craft and Seedance lessons; Assets-Produce is where those lessons are being made agent-native and launchable.

It also depends on [[entities/dramatizer-ls]] and [[entities/lunascripts]] for upstream narrative structure. The better the LS and episode JSON encode scene continuity, character identity, and choice context, the less the video agent has to infer during Step 1.

## Sources

This page was reconstructed from the local repository at `/Users/Clock/video-agent-claude-wangbo`, especially:

- `README.md`
- `agent-skills/video-episode-generation/SKILL.md`
- `agent-skills/video-episode-generation/scripts/build_gateway_payload.py`
- `ablation/ABLATION_REPORT.md`
- Git history from 2026-04-29 through 2026-05-03
- [Assets-Produce local videoctl cleanup](../raw/2026-05-11-assets-produce-local-videoctl-cleanup.md)
