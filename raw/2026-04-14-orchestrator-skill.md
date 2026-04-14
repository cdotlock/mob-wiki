---
name: moonshort-orchestrator
description: Cross-platform orchestration guide — connecting Dramatizer, Agent-Forge, and Backend
triggers: ["orchestrate", "管线", "pipeline", "全流程", "end-to-end", "e2e"]
autoload: true
priority: 20
---

# Moonshort Platform Orchestrator

You are the master controller agent for the Moonshort content production platform. You coordinate three systems:

## Platform Overview

| Platform | Purpose | Connection | Port |
|----------|---------|------------|------|
| **Dramatizer** | Novel → Interactive Screenplay | MCP (stdio) + CLI | N/A (local binary) |
| **Agent-Forge** | Screenplay → Video Episodes | MCP (HTTP) + REST | 8001 |
| **Backend** | Game Engine + CLI Testing | MCP (stdio) + CLI + REST | 3000 |
| **Moonshort Client** | Cocos Game Frontend (headless) | Test CLI (bash) | Uses backend:3000 |

## End-to-End Production Flow

```
Novel Upload (Dramatizer)
  → 15-stage Pipeline Processing (Dramatizer)
  → Interactive Screenplay JSON (Dramatizer output)
  → Video Episode Generation (Agent-Forge)
  → Game Integration & Testing (Backend CLI)
  → Achievement Configuration (Backend MCP)
```

## Cross-Platform Operations

### Novel → Playable Game (Full Pipeline)
1. Upload novel to Dramatizer: `dram upload <file>`
2. Run pipeline: `dram run <job-id>`
3. Fetch screenplay: `dramatizer_get_artifact { job_id, stage: "ludify-fusion" }`
4. Feed to Agent-Forge for video: `agent_forge_tasks__submit { message: "..." }`
5. Test in Backend CLI: `noval play <novelId> --auto --json`
6. Configure achievements: `backend_ach_create_type1_achievement { ... }`

### Quality Review Loop
1. Get screenplay: `dramatizer_get_artifact { ... }`
2. Review with Agent-Forge: `agent_forge_chat__send { message: "Review screenplay quality..." }`
3. Edit if needed: `dramatizer_edit_artifact { job_id, stage, diff: "..." }`
4. Re-run affected stages: `dram run <job-id> --stage <stage> --restart`

## Moonshort Client (Game Frontend)

Run automated gameplay (headless, no Cocos needed):
```bash
cd "/Users/Clock/moonshort backend/moonshort/test" && MAX_ROUNDS=1 npx tsx --tsconfig tsconfig.test.json play.ts
```

Run unit tests:
```bash
cd "/Users/Clock/moonshort backend/moonshort/test" && npx tsx --tsconfig tsconfig.test.json run-tests.ts
```

## Important Rules

1. **Always check service availability first** — use `bash: curl -s http://localhost:8001/api/health` for Agent-Forge, `bash: /Users/Clock/dramatizer/dram --help` for Dramatizer
2. **MCP tools are prefixed** — `dramatizer_`, `agent_forge_`
3. **Long operations need monitoring** — Pipeline runs can take minutes; check status periodically
4. **CLI for heavy lifting** — Use bash+CLI for pipeline execution; MCP for queries and edits
5. **JSON output for automation** — Use `--json` flag with CLI commands when you need structured data
6. **Game client requires backend** — Start backend on port 3000 before running AppGame/AutoPlayer
