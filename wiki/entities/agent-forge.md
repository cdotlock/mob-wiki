---
title: Agent-Forge
tags: [nextjs, mcp, video, agent, llm]
sources: [raw/2026-04-14-agent-forge-skill.md, raw/2026-04-14-mobai-agent-memory.md]
created: 2026-04-14
updated: 2026-04-14
---

Next.js application that converts interactive screenplays into video episodes using AI agents. Exposes 48 MCP tools via HTTP StreamableHTTP, a full REST API, and an agent chat loop.

## Tech Stack

- **Framework:** Next.js 16 (App Router)
- **DB:** PostgreSQL (Prisma ORM v6.6)
- **MCP:** @modelcontextprotocol/sdk (HTTP StreamableHTTP)
- **LLM:** OpenAI-compatible (configurable)
- **UI:** Ant Design + TailwindCSS
- **Repo:** github.com/Rydia-China/Agent-Forge

## MCP Architecture

Registry-based with pluggable providers:

**Core Providers (always active):** skills, mcp_manager, ui, memory, sync
**Catalog Providers (lazy-loaded):** biz_db, apis, video_mgr, langfuse, subagent, oss

MCP endpoints: `/mcp` (all tools) and `/mcp/[provider]` (scoped)

## Dynamic MCP Sandbox

QuickJS (quickjs-emscripten) sandbox for user-defined MCP tools. Code must use CommonJS `module.exports` format. Built-in globals: `console`, `fetch`/`fetchSync`, `getSkill`, `callToolSync`. No `JSON` global.

## CLI: forge-eval

Evaluation harness at `cli/`. Commands: `run`, `report`, `promote`, `diff`, `compare`, `trend`. Connects to Agent-Forge API at localhost:8001 for task submission and SSE polling.

## Related

- [[entities/mobai-agent]]
- [[entities/dramatizer]]
- [[concepts/cli-gateway-protocol]]

## Sources

- [Agent-Forge skill](../raw/2026-04-14-agent-forge-skill.md)
