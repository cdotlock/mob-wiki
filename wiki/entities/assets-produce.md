---
title: Assets-Produce
tags: [agent, opencode, assets, video, prompt, cli]
sources: [raw/2026-05-11-assets-produce-local-videoctl-cleanup.md]
created: 2026-05-11
updated: 2026-05-11
---

Assets-Produce is the agent-native asset production platform that turns prompt workflows into a local CLI, opencode tools, and eventually WebUI/API surfaces. As of 2026-05-11, it has absorbed the useful video-prompt lessons from [[entities/video-agent-claude-wangbo]] and the image/material prompt lessons from [[entities/agent-forge]], while removing old reference folders from the active repository.

## Repository Identity

| Field | Value |
|---|---|
| Local path | `/Users/Clock/lunaverse/assets-produce` |
| Remote | `https://github.com/cdotlock/assets-produce.git` |
| Branch | `main` |
| Latest documented cleanup commit | `a932935 chore: clean reference folders and add local videoctl` |
| Runtime base | opencode fork under `agent/` |
| Web surface | `web/` creator workstation |
| Local knowledge root | `knowledge/novel-to-video/` |
| Prompt fixture root | `video-agent-test/` |

The repository is no longer a container for large external reference projects. `legacy/`, `cli-example/`, and `video-agent-test/agent-skills/` were deleted after their useful rules were distilled into local knowledge files and tool implementations.

## Product Role

Assets-Produce is meant to be the production-facing replacement for scattered asset-generation workflows. It keeps the [[concepts/four-layer-philosophy]] shape:

| Layer | Assets-Produce implementation |
|---|---|
| SKILL | Source material is local in `knowledge/`; Langfuse upload happens only after explicit instruction. |
| CLI | `agent/dist/agent.mjs` and source-path `agent/packages/opencode/src/index.ts` expose commands and schemas. |
| Tool | Atomic opencode tools such as image generators, video generators, and the local `videoctl` prompt workflow tool. |
| API | External providers such as OSS, Langfuse, image generation, and video generation remain behind explicit atomic tools. |

The important architectural decision is that orchestration stays agent-native. The repository must not reintroduce a hardcoded video workflow service. The agent reads rules, writes prompt artifacts, calls deterministic local tools, and only calls media-generation tools when the user explicitly authorizes that stage.

## Current Repository Layout

| Path | Role |
|---|---|
| `agent/` | opencode-based agent and CLI base. This is a standalone Bun monorepo inherited from upstream opencode. |
| `web/` | creator workstation frontend. It should wrap CLI/API behavior rather than implement separate business logic. |
| `knowledge/novel-to-video/` | self-contained local source of truth for prompt workflow knowledge. |
| `video-agent-test/` | prompt-only scripts/assets fixture and video CLI reference code. The old skill package was removed. |
| `docs/superpowers/specs/` | master spec, phase plans, and verification reports. |

The removed folders are intentionally not tracked:

| Removed path | Reason |
|---|---|
| `legacy/` | Old Agent-Forge snapshot. Keeping it in-tree made the active repository noisy and encouraged stale workflow references. |
| `cli-example/` | Old MiniMax CLI design reference. Its useful command-contract lessons were already incorporated. |
| `video-agent-test/agent-skills/` | Old video skill package. The active prompt lessons now live under `knowledge/novel-to-video/`. |

## Local Knowledge Pack

`knowledge/novel-to-video/` is the current self-contained source for novel/script-to-prompt work. It is intentionally inert: no file is named `SKILL.md`, and nothing in the directory is automatically loaded as a runtime skill.

Active files:

| File | Purpose |
|---|---|
| `prompt-only-contract.md` | Defines the default local prompt-only boundary for AB tests and prompt authoring. |
| `image-style-presets.json` | Distilled Agent-Forge image/material prompt presets. |
| `video-prompt-standard.md` | Video prompt structure and character-reference rules. |
| `character-reference-policy.md` | Character outfit/source-image authority rules. |
| `seedance-core-lessons.md` | Compact Seedance model behavior lessons. |
| `director-playbook-core.md` | Compact shot/director rules. |
| `shot-id-policy.md` | Shot ID and reference-image ordering rules. |
| `nine-section-template.md` | Empty nine-section video prompt scaffold. |
| `videoctl-tool-reference.md` | Local opencode `videoctl` tool usage and boundaries. |
| `langfuse-draft.md` | Single-file future Langfuse skill body draft. |
| `source-inventory.json` | Keep/drop audit of source material. |

The rule is: local first, Langfuse later. Langfuse skill bodies are rebuilt from this pack only after explicit user instruction.

## Prompt-Only Contract

Prompt-only is the default mode for AB tests and prompt authoring. It produces prompt artifacts, not media:

| Artifact | Description |
|---|---|
| image prompt specs | Structured image/material prompt intents for scene, portrait, costume/update, or shot anchor images. |
| video prompt markdown | A full `prompt.md` with YAML frontmatter and nine-section body. |
| legacy-compatible prompt JSON | Compatibility object carrying key fields such as prompt, definition, duration, and references. |
| self-review | Agent-authored check of characters, scene, forbidden content, and consistency. |
| trace summary | Files read, reasoning path summary, and image/video consistency notes. |
| manifest | Machine-readable list of artifacts created for the run. |

The boundary explicitly excludes image generation, video generation, upload, live URL validation, live submit, download, frame extraction, crop, concat, and remote skill loading.

## Local `videoctl` Tool

`videoctl` is an opencode built-in tool in Assets-Produce. It wraps the local TypeScript `agent video` implementation inside opencode and replaces shell usage of old Go or script-based `videoctl` commands during prompt workflow verification.

Supported operations:

| Operation | Purpose | Live media? |
|---|---|---|
| `payload` | Parse `prompt.md` and build gateway request JSON locally. | No |
| `validate` | Check media references and sidecar URLs. | No generation; can touch URLs when explicitly used. |
| `submit_dry_run` | Write `request.json` and `state.json` into a local run directory. | No |
| `status` | Read a local dry-run state directory. | No |
| `prompt_review` | Score one prompt against the local checklist. | No |
| `prompt_compare` | Compare candidate and reference prompts. | No |

The tool intentionally does not expose live video submit, upload, download, frame extraction, concat, crop, or any image/video generation path. This makes it safe for prompt-only verification and for real-agent AB tests where media generation must not run.

## CLI Surface

The deterministic video-prompt commands are available both through the CLI and through opencode tools:

```bash
agent video payload <prompt.md> --project-root <root>
agent video validate <prompt.md> --project-root <root> --allow-non-oss --json
agent video submit <prompt.md> --dry-run --run-dir /tmp/video-run --project-root <root>
agent video status /tmp/video-run
agent video prompt review <prompt.md> --json
agent video prompt compare <candidate.md> <reference.md> --json

agent tools call videoctl --json '{"operation":"prompt_review","promptPath":"<prompt.md>"}' --output json
```

`agent video submit` requires `--dry-run` on this path. Live video generation remains a separate explicitly authorized path through the normal media-generation tools.

## Real-Agent AB Harness

`scripts/phase7-real-agent-ab.mjs` runs real candidate/reference prompt workflow AB tests in isolated workspaces. The harness records:

- elapsed time
- token totals
- cost
- assistant message count
- files read
- tool calls
- behavior score
- prompt review score
- prompt compare score
- final effect score

Candidate runs must use the compact local knowledge pack. They are penalized if they call media tools, remote skills, old shell `videoctl` live commands, `curl`, `wget`, or generated-media workflows.

The current harness uses prompt-only cases drawn from Silver Moon Manor EP2. It should be rerun after major prompt-rule changes, especially before claiming that Assets-Produce fully replaces the prior workflow.

## Relationship To Agent-Forge

[[entities/agent-forge]] remains the historical source for image/material prompt style lessons and older video-production platform ideas. Assets-Produce does not embed Agent-Forge as a runtime dependency and does not keep an Agent-Forge snapshot in `legacy/`.

The important borrowed lessons are now represented as local artifacts:

- `image-style-presets.json` keeps distilled Agent-Forge image/material prompt templates.
- `langfuse-draft.md` is the eventual upload body for Langfuse once the local source is approved.
- `source-inventory.json` records what was kept, dropped, or explicitly not uploaded.

## Relationship To Video Agent Claude Wangbo

[[entities/video-agent-claude-wangbo]] remains the historical source for shot-level prompt craft, Seedance lessons, reference ordering, and nine-section prompt structure. Assets-Produce absorbed the useful parts into `knowledge/novel-to-video/` and into the local `videoctl` tool.

The old `video-agent-test/agent-skills/` copy was removed from Assets-Produce because it contained production execution SOP, upload/generation behavior, reviewer sub-agent rules, mutable memory, and heavy incident logs that were too costly for prompt-only candidate runs. The fixture directory remains useful for scripts, episode data, local assets, and prompt-only AB references.

## Verification Status

The 2026-05-11 cleanup and local tool integration were verified with:

```bash
bun --cwd=agent/packages/opencode test test/video/video.test.ts test/tool/tool-define.test.ts
bun --cwd=agent/packages/opencode run typecheck
bun run agent:build
node --check scripts/phase7-real-agent-ab.mjs
jq '.' knowledge/novel-to-video/source-inventory.json >/dev/null
jq '.[].name' knowledge/novel-to-video/image-style-presets.json >/dev/null
git diff --check
```

Results:

| Check | Result |
|---|---|
| video/tool tests | 12 pass, 0 fail |
| TypeScript typecheck | pass |
| agent build | pass |
| AB harness syntax | pass |
| knowledge JSON | pass |
| diff whitespace | pass |
| removed directories | absent from disk and git tracking |

## Operating Rules

When changing Assets-Produce:

1. Keep reference material in `knowledge/` or docs, not as embedded external projects.
2. Keep prompt authoring prompt-only unless the user explicitly authorizes media generation.
3. Use local opencode `videoctl` for deterministic video prompt workflow checks.
4. Do not shell out to old `scripts/bin/videoctl` for opencode agent workflows.
5. Do not reintroduce a hardcoded orchestration/workflow service.
6. Rebuild and test `agent/dist/agent.mjs` after changing built-in opencode tools.
7. Treat Langfuse upload as a later explicit operation, not as part of local cleanup.

## Related

- [[concepts/four-layer-philosophy]]
- [[entities/agent-forge]]
- [[entities/video-agent-claude-wangbo]]
- [[entities/mobai-agent]]

## Sources

- [Assets-Produce local videoctl cleanup](../raw/2026-05-11-assets-produce-local-videoctl-cleanup.md)
