---
title: Dramatizer
tags: [go, cli, pipeline, llm, screenplay]
sources: [raw/2026-04-14-dramatizer-skill.md, raw/2026-04-14-mobai-agent-memory.md]
created: 2026-04-14
updated: 2026-04-14
---

Go binary that converts novels into interactive screenplays through a 15-stage LLM pipeline. Exposes CLI (Cobra), HTTP REST API (Chi), MCP server (mcp-go), and interactive TUI (Bubble Tea).

## Tech Stack

- **Language:** Go 1.25.0, single binary (~24MB)
- **CLI:** Cobra (33 commands)
- **HTTP:** Chi router v5 (REST API + SSE progress streaming)
- **MCP:** mark3labs/mcp-go v0.46.0 (stdio + HTTP transport)
- **TUI:** Bubble Tea + Bubbles
- **DB:** SQLite (dev) / PostgreSQL (prod) via abstract Store interface
- **Repo:** github.com/AugustZAD/Dramatizer

## Integration Points

| Mode | Command | Use Case |
|------|---------|----------|
| MCP stdio | `dram mcp` | Local agent connection |
| MCP HTTP | `dram mcp --http --port 9002` | Remote agent connection |
| CLI Gateway | `dram gateway --port 9001` | Remote CLI execution |
| REST API | `dram serve --port 3000` | Web client / direct API |

## 15-Stage Pipeline

1. chapter-split, 2. chapter-summary, 3. world-build, 4. character-forge, 5. skeleton, 6. ludify-analyze, 7. ludify-tree, 8. ludify-minor, 9. ludify-dice, 10. ludify-fusion, 11. scene-split, 12. scene-write, 13. minigame-inject, 14. image-prompt, 15. output

## MCP Tools (14)

**Read:** list_novels, get_novel, list_jobs, get_job, list_artifacts, get_artifact, list_snapshots, get_snapshot
**Write:** create_job, set_artifact, edit_artifact, stop_job

## Related

- [[entities/mobai-agent]]
- [[concepts/cli-gateway-protocol]]

## Sources

- [Dramatizer skill](../raw/2026-04-14-dramatizer-skill.md)
