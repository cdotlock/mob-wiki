---
title: Cloud Deployment Architecture
tags: [deployment, cloud, architecture, distributed]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

Analysis of how the Moonshort platform transitions from a local development setup (all services on one machine) to a distributed cloud deployment across multiple servers, and the architectural changes required.

## Problem

In local development, [[entities/mobai-agent]] connects to services via:
- **stdio MCP** — spawns local subprocess (Dramatizer)
- **localhost HTTP MCP** — connects to local server (Agent-Forge)
- **local bash** — executes CLI tools directly (Backend, Client)

None of these work across network boundaries except HTTP MCP.

## Solution: Two Complementary Layers

### 1. CLI Gateway (remote CLI execution)

Each service runs a [[entities/cli-gateway]] microservice that accepts HTTP requests and executes CLI commands locally. The agent's `cli_run` tool routes commands to the appropriate gateway based on `config.yaml`.

```
mobai-agent (cloud)
  cli_run("dram run job-1")
  --> routes to Dramatizer gateway at :9001
  --> gateway spawns "dram run job-1" locally
  --> returns stdout/stderr/exitCode via HTTP
```

### 2. HTTP MCP (remote tool invocation)

All MCP connections use HTTP transport:
- [[entities/agent-forge]]: Already HTTP StreamableHTTP (change URL only)
- [[entities/dramatizer]]: New `dram mcp --http --port 9002` mode

### 3. Server Layer (remote agent access)

[[entities/mobai-agent]] itself is accessible remotely via [[concepts/server-layer]] (HTTP/WebSocket). Local users connect through the web client instead of the terminal TUI.

## Deployment Topology

```
                    mobai-agent (Server A)
                    +-- REST API + WebSocket
                    +-- Web client
                    |
         +----------+----------+----------+
         |          |          |          |
    Dramatizer  Agent-Forge  Backend   Client
    (Server B)  (Server C)   (Server D) (CI/CD)
    :9001 GW    :9001 GW     :9002 GW  :9003 GW
    :9002 MCP   :8001 MCP
```

## Config Change (mobai-agent)

```yaml
# MCP: change URLs from localhost to cloud endpoints
mcp:
  servers:
    agent-forge:
      url: "https://forge.moonshort.io/mcp"
      transport: "http"
    dramatizer:
      url: "https://dram.moonshort.io/mcp"
      transport: "http"   # was stdio

# CLI: route commands to gateways
cli:
  gateways:
    dramatizer:
      url: "https://dram.moonshort.io:9001"
      tools: ["dram"]
    backend:
      url: "https://backend.moonshort.io:9002"
      tools: ["noval"]
```

## What Doesn't Change

- CLI binaries (dram, noval, test scripts) — unchanged
- MCP tool definitions — unchanged
- Agent's progressive discovery loop — unchanged
- Skills and memory system — unchanged
- The [[concepts/four-layer-philosophy]] — all four layers work identically

## Migration Path

| Priority | Task | Effort |
|----------|------|--------|
| P0 | Deploy CLI Gateways alongside each service | Per-service config |
| P0 | Switch Dramatizer MCP to HTTP mode | Flag change |
| P1 | Deploy mobai-agent server mode | Config change |
| P1 | Update config.yaml URLs per environment | Env vars |
| P2 | Build web client dist | One-time build |

## Related

- [[entities/cli-gateway]]
- [[concepts/cli-gateway-protocol]]
- [[concepts/server-layer]]
- [[concepts/four-layer-philosophy]]

## Sources

- [Design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
