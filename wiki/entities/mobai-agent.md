---
title: mobai-agent
tags: [agent, orchestrator, moonshort, bun]
sources: [raw/2026-04-14-mobai-agent-memory.md, raw/2026-04-14-orchestrator-skill.md]
created: 2026-04-14
updated: 2026-04-14
---

Master AI agent orchestrator for the Moonshort content production platform. Drives an end-to-end pipeline that converts novels into screenplays, videos, and playable games through natural language commands.

## Architecture

Built on Bun runtime with Vercel AI SDK. Supports Anthropic, OpenAI, and any OpenAI-compatible LLM provider. Default model: Claude Sonnet 4.6 via ZenMux aggregator.

**Core Modules:**
- `src/core/runner.ts` — LLM loop engine (tool calls, self-correction)
- `src/core/loop.ts` — Orchestration (sessions, skills, memory, MCP)
- `src/core/compaction.ts` — 4-level token management (200K context window)
- `src/tool/` — 11 builtin tools + dynamic MCP tool loading
- `src/server/` — HTTP/WebSocket server for remote access
- `src/tui/` — Terminal UI (Ink/React)
- `web/` — Lightweight web chat client (Vite + React + TailwindCSS)

**Execution Modes:**
- Interactive TUI: `bun run dev`
- Single query: `bun run dev -- --run "question"`
- Pipe input: `echo "query" | bun run dev`
- Server mode: `bun run dev -- --server --port 3100`
- Session resume: `bun run dev -- --session=<id>`

## Tools (11 Builtin)

| Tool | Purpose |
|------|---------|
| `bash` | Raw shell execution |
| `read_file` | Read with line numbers |
| `write_file` | Create/overwrite files |
| `edit_file` | Precise line-based replacement |
| `grep` | Regex search |
| `glob` | File pattern matching |
| `memory_read` | Read MEMORY.md / SOUL.md / USER.md |
| `memory_write` | Write to memory files (auto git commit) |
| `discover_cli` | Scan available CLI tools (local + remote gateways) |
| `cli_help` | Fetch/cache CLI help docs (7-day TTL) |
| `cli_run` | Execute CLI with auto-recovery + gateway routing |

## MCP Connections

| Server | Transport | Tools |
|--------|-----------|-------|
| [[entities/agent-forge]] | HTTP StreamableHTTP (:8001) | 48 tools |
| [[entities/dramatizer]] | stdio (or HTTP with `--http`) | 14 tools |

## Server Layer

HTTP/WebSocket server (`src/server/http.ts`) via `Bun.serve()`:

**REST API:** `/api/health`, `/api/sessions`, `/api/skills`, `/api/memory/:type`
**WebSocket:** `/ws` — real-time chat streaming with tool progress events
**Web client:** Served from `web/dist/` (Vite + React + TailwindCSS)

## CLI Gateway Routing

When `cli.gateways` is configured in `config.yaml`, `cli_run` transparently routes commands to remote [[concepts/cli-gateway-protocol]] servers. The agent is unaware of remote execution — same progressive discovery and self-correction loop works identically.

## Memory System

Three markdown files in `memory/` (git-tracked):
- **MEMORY.md** — Facts: platform locations, MCP counts, CLI tools, DB details
- **SOUL.md** — Agent persona: language preference, tool strategy, communication style
- **USER.md** — User profiles and preferences

## Related

- [[entities/dramatizer]]
- [[entities/agent-forge]]
- [[entities/moonshort-backend]]
- [[entities/moonshort-client]]
- [[concepts/four-layer-philosophy]]
- [[concepts/cli-gateway-protocol]]

## Sources

- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
- [Orchestrator skill](../raw/2026-04-14-orchestrator-skill.md)
