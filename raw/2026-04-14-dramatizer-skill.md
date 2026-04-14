---
name: dramatizer-pipeline
description: Dramatizer screenplay pipeline operation guide — novel-to-interactive-screenplay conversion
triggers: ["dramatizer", "剧本", "pipeline", "screenplay", "novel", "小说", "dram", "剧情", "分支"]
autoload: false
priority: 10
---

# Dramatizer Pipeline — Operation Guide

Dramatizer converts long novels into interactive mini-drama screenplays via a 15-stage LLM pipeline.

## Architecture

- **Binary**: `/Users/Clock/dramatizer/dram`
- **MCP**: Connected as `dramatizer` (stdio) — tools prefixed `dramatizer_`
- **CLI**: `bash` tool with `/Users/Clock/dramatizer/dram <command>`
- **Database**: SQLite (dev) / PostgreSQL (prod)

## MCP Tools Available

### Read Operations
- `dramatizer_list_novels` — List uploaded novels (filter by status, limit)
- `dramatizer_get_novel` — Get novel details by ID
- `dramatizer_list_jobs` — List processing jobs (filter by novel_id, status)
- `dramatizer_get_job` — Get job details including pipeline stage progress
- `dramatizer_list_artifacts` — List outputs for a job by stage
- `dramatizer_get_artifact` — Get specific stage output (JSON content)
- `dramatizer_list_snapshots` — List LLM call history for a job
- `dramatizer_get_snapshot` — Get full LLM input/output record

### Write Operations
- `dramatizer_create_job` — Create new processing job for a novel
- `dramatizer_set_artifact` — Inject controller artifacts (prompt-preamble, target-episodes)
- `dramatizer_edit_artifact` — Diff-based editing of stage outputs
- `dramatizer_stop_job` — Cancel a running job

## 15-Stage Pipeline

### Phase 1: Content Extraction
1. `skeleton` — Extract protagonist + core characters (first 10k chars)
2. `extract` — Parallel scene extraction (resumable)
3. `resolve` — Unify character names across chapters
4. `bible` — Generate narrative authority document (3-sub-stage)
5. `judge` — Quality review with conditional routing
6. `final` — Merge extracted data into canonical form

### Phase 2: Screenplay Architecture
7. `refine-map` — Episode planning (restartable)
8. `refine-write` — Write episodes (resumable)

### Phase 3: Interactive Branches
9. `ludify-analyze` — Story structure analysis
10. `ludify-tree` — Story tree design (Agent Loop: think→draft→critique→revise)
11. `ludify-growth` — Growth choice points (parallel)
12. `ludify-minor` — Minor branches (1-3 episodes, return to main)
13. `ludify-badend` — Bad endings (narrative purpose)
14. `ludify-route` — Independent subplots (max 2 parallel)
15. `ludify-fusion` — Merge all branches into final v2.0 story tree

## Common Workflows

### Upload and Process a Novel
```
1. Use bash: /Users/Clock/dramatizer/dram upload <file> --title "My Novel"
2. dramatizer_create_job { novel_id: N }
3. Use bash: /Users/Clock/dramatizer/dram run <job-id>
4. Monitor: dramatizer_get_job { job_id: N }
5. Fetch output: dramatizer_get_artifact { job_id: N, stage: "ludify-fusion" }
```

### Inject Quality Constraints Before Running
```
1. dramatizer_set_artifact { job_id: N, stage: "prompt-preamble", content: "..." }
2. dramatizer_set_artifact { job_id: N, stage: "target-episodes", content: "12" }
```

### Re-run a Single Stage
```
bash: /Users/Clock/dramatizer/dram run <job-id> --stage bible --restart
```

### Check Pipeline Progress
```
bash: /Users/Clock/dramatizer/dram pipeline status <job-id> --json
```

## Key Constraints
- LLM calls are snapshotted to DB for auditability
- Artifact existence = stage completion (recovery mechanism)
- Default model: Grok 4.1 Fast via Zenmux
- Config files: `config/pipeline.yaml`, `config/stage-llm.yaml`
