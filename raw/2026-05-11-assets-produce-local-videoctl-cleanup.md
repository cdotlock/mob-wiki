---
title: Assets-Produce Local VideoCtl Cleanup
date: 2026-05-11
source_repo: /Users/Clock/moonshort/assets-produce
commit: a932935
---

# Assets-Produce Local VideoCtl Cleanup

On 2026-05-11, `assets-produce` was cleaned and pushed to `origin/main` at commit `a932935 chore: clean reference folders and add local videoctl`.

## Repository State

`assets-produce` is the agent-native multi-format asset production platform based on opencode. The live repository now keeps only runtime code, local knowledge, prompt fixtures, and documentation:

- `agent/` — opencode-based agent and CLI base.
- `web/` — creator workstation.
- `knowledge/novel-to-video/` — self-contained local source of truth for novel/script to prompt workflow.
- `video-agent-test/` — prompt-only scripts/assets fixture and video CLI reference code.
- `docs/superpowers/specs/` — architecture specs, phase plans, and verification reports.

The following old reference folders were removed from the active repository and are no longer tracked by git:

- `legacy/`
- `cli-example/`
- `video-agent-test/agent-skills/`

The useful prompt lessons from those references were distilled into `knowledge/novel-to-video/`.

## Local Knowledge Pack

The active local prompt workflow is `knowledge/novel-to-video/`. It is intentionally inert: no file is named `SKILL.md`, and nothing is auto-loaded as a runtime skill.

Active files:

- `prompt-only-contract.md`
- `image-style-presets.json`
- `video-prompt-standard.md`
- `character-reference-policy.md`
- `seedance-core-lessons.md`
- `director-playbook-core.md`
- `shot-id-policy.md`
- `nine-section-template.md`
- `videoctl-tool-reference.md`
- `langfuse-draft.md`
- `source-inventory.json`

Current rule: keep the workflow local and self-contained first. Langfuse skill bodies should be rebuilt from `langfuse-draft.md` or a compiled equivalent only after explicit user instruction.

## Prompt-Only Boundary

Prompt-only mode means producing prompt artifacts only:

- image prompt specs
- video prompt markdown
- legacy-compatible prompt JSON
- self-review
- trace summary
- manifest

It explicitly excludes:

- image generation
- video generation
- media upload
- live URL validation
- live submit
- download
- frame extraction
- crop / concat
- remote skill loading

## Local `videoctl` Tool

`assets-produce` now has a built-in opencode tool named `videoctl`. It wraps the local TypeScript `agent video` implementation and is meant to be used inside opencode instead of shelling out to old `scripts/bin/videoctl` commands.

Supported operations:

- `payload` — parse `prompt.md` and build the gateway request JSON locally.
- `validate` — check media references and sidecar URLs.
- `submit_dry_run` — write `request.json` and `state.json` into a local run directory without submitting a live job.
- `status` — read a local dry-run run directory state.
- `prompt_review` — score one prompt against the local checklist.
- `prompt_compare` — compare a candidate prompt with a reference prompt.

The tool intentionally does not expose live video submission, upload, download, frame extraction, concat, crop, or any media-generation path.

## CLI Surface

The command-line interface also exposes deterministic prompt-only video helpers:

```bash
agent video payload <prompt.md> --project-root <root>
agent video validate <prompt.md> --project-root <root> --allow-non-oss --json
agent video submit <prompt.md> --dry-run --run-dir /tmp/video-run --project-root <root>
agent video status /tmp/video-run
agent video prompt review <prompt.md> --json
agent video prompt compare <candidate.md> <reference.md> --json

agent tools call videoctl --json '{"operation":"prompt_review","promptPath":"<prompt.md>"}' --output json
```

Live video submit is intentionally disabled on this path; `agent video submit` requires `--dry-run`.

## AB Harness

`scripts/phase7-real-agent-ab.mjs` is the real-agent AB harness. It was updated so the candidate path reads from the compact local knowledge pack instead of loading the old Langfuse `novel-to-video` skill or the deleted `video-agent-test/agent-skills/` tree.

The harness writes isolated workspaces and records:

- elapsed time
- token totals
- cost
- tool behavior
- files read
- prompt review score
- prompt compare score
- final effect score

Candidate runs are explicitly forbidden from calling media tools, remote skills, live submit, upload, download, frame extraction, crop, concat, `curl`, or ad hoc HTTP scripts.

## Verification

The cleanup and local tool integration were verified with:

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

- video/tool tests: 12 pass, 0 fail
- typecheck: pass
- build: pass
- script syntax: pass
- knowledge JSON: pass
- diff whitespace: pass
- `legacy/`, `cli-example/`, and `video-agent-test/agent-skills/` absent from disk and git tracking
