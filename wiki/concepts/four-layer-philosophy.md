---
title: SKILL / CLI / MCP / API Four-Layer Philosophy
tags: [architecture, agent, design-pattern]
sources: []
created: 2026-04-14
updated: 2026-04-14
---

Design framework for systems that let AI agents operate complex platforms. Each layer addresses a different cognitive state an agent can be in, ensuring there is always an appropriate entry point regardless of the agent's level of familiarity.

## The Four Layers

**SKILL (Knowledge Layer)** — "How to think about the problem"
Markdown injected into LLM context. Provides direction, constraints, decision frameworks. Decoupled from implementation — CLI commands can be renamed without invalidating SKILL.

**CLI (Discovery & Orchestration Layer)** — "What to call, in what order"
Packaged tool with progressive discovery (`schema`, `help`, `--dry-run`). Integrates large pipelines into single commands. Internalizes auth, error classification, audit as cross-cutting concerns.

**MCP (Direct Access Layer)** — "Just do this specific thing, efficiently"
Fine-grained tool invocation. Skips CLI ceremony when the agent already knows what capability to call. CLI is for exploration, MCP is for execution — complementary, not competing.

**API (Raw Capability Layer)** — "What the system can do"
Invisible foundation. Agent should never call APIs directly. Exposed only as CLI's raw fallback, ensuring the agent is never stuck.

## Cognitive State Decision Tree

```
Agent faces a task:
  +-- Doesn't know how to think about it --> Read SKILL
  +-- Knows direction, not specific command --> Use CLI progressive discovery
  +-- Knows exactly what to call, wants speed --> Use MCP direct invocation
  +-- Nothing else works --> Use CLI raw API fallback
```

## Core Principles

1. SKILL gives direction, not means
2. CLI is the sole execution entry for external agents
3. CLI and MCP complement, never compete
4. API is invisible by design
5. Layer weights are elastic (MCP-heavy architectures need stronger SKILL)
6. Design for every cognitive state

## Architecture Variants in Moonshort

- **[[entities/dramatizer]]**: CLI wraps API directly. Rich hand-written shortcuts, MCP supplements for server-side intelligence.
- **[[entities/agent-forge]]**: CLI wraps MCP as core transport. SKILL becomes essential as CLI surface is dynamically generated.

## Related

- [[entities/mobai-agent]]
- [[concepts/cli-gateway-protocol]]

## Sources

Derived from cross-project analysis documented in the project's CLAUDE.md.
