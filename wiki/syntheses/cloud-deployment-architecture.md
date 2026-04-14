---
title: "Cloud Deployment Architecture"
tags: [deployment, cloud, architecture, distributed, migration]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

# Cloud Deployment Architecture

## Problem Statement

### Current Local Setup

In the local development environment, all five Moonshort platform services run on a single machine. [[entities/mobai-agent]] connects to them through three transport mechanisms:

1. **stdio MCP** -- The agent spawns the Dramatizer MCP server as a local subprocess using `StdioClientTransport`. The agent's process directly writes to the subprocess's stdin and reads from its stdout. This requires the `dram` binary to exist on the same machine and in the same filesystem as the agent process.

2. **localhost HTTP MCP** -- The agent connects to Agent-Forge's MCP server via HTTP at `http://localhost:8001/mcp`. This works because both processes bind to the same machine's loopback interface.

3. **local bash** -- The agent executes CLI tools (for Backend and Moonshort Client) via `Bun.spawn()`, which spawns processes directly on the local machine. This requires the CLI entry scripts (`cli/bin/noval.ts`, `test/play.ts`) and their dependencies to exist in the local filesystem.

### What Breaks When Going Cloud

When services are distributed across multiple servers, each of these local transport mechanisms breaks:

**stdio MCP (subprocess) breaks completely.** The `StdioClientTransport` spawns a subprocess on the agent's machine. If the Dramatizer runs on a different server, the agent cannot spawn its binary. There is no subprocess to connect to. The MCP client's `command` and `args` configuration (e.g., `command: "/Users/Clock/dramatizer/dram"`, `args: ["mcp"]`) references a path that does not exist on the agent's server.

**Local bash (same machine) breaks completely.** `Bun.spawn(["npx", "tsx", "cli/bin/noval.ts", ...])` requires the Backend's source code, node_modules, and runtime to be present on the agent's machine. When the Backend runs on a different server, none of these exist locally. The spawn call fails with ENOENT.

**Hardcoded localhost URLs break for all HTTP connections.** `http://localhost:8001/mcp` assumes Agent-Forge is running on the same machine. When Agent-Forge runs on Server C, the agent must connect to `http://forge.server-c.internal:8001/mcp` instead.

**Local filesystem paths in CLI commands break.** Commands like `dram run <job-id>` reference input and output files using local filesystem paths. When the Dramatizer runs on a different machine, the agent cannot access its filesystem directly. Job artifacts stored at `/Users/Clock/dramatizer/artifacts/` are not reachable from the agent's server.

The only transport that survives the transition to cloud without changes is HTTP MCP when the URL is updated to point to the correct host. This is the key observation that drives the solution architecture: HTTP is the universal transport that works across network boundaries.

## Solution Architecture: Three Complementary Layers

The solution does not require replacing the existing architecture. It adds three complementary layers that bridge the local-to-cloud gap while preserving everything that already works.

### Layer 1: CLI Gateway (Remote CLI Execution)

Each service deploys a [[entities/cli-gateway]] microservice alongside its main process. The gateway accepts HTTP requests conforming to the [[concepts/cli-gateway-protocol]], executes CLI commands locally on the machine where the service runs, and returns stdout/stderr/exitCode over HTTP.

On the agent side, `cli_run` gains a routing layer. Before executing a command locally, it checks if any configured gateway handles the command. If a gateway match is found, the request is sent to the gateway via HTTP. If no match is found, the command is executed locally (preserving backward compatibility with the local development workflow).

The routing is transparent to the agent's reasoning layer. The agent calls `cli_run` with a command name and arguments. Whether that command runs locally or remotely is a configuration concern handled by the tool implementation, not a decision the agent needs to make.

**Topology: Agent connecting to four CLI Gateways**

```
                          mobai-agent
                        (Agent Server)
                             |
            +----------------+----------------+
            |                |                |
   HTTP POST /exec   HTTP POST /exec   HTTP POST /exec
            |                |                |
            v                v                v
  +------------------+  +-----------+  +------------------+
  | Dramatizer GW    |  | Backend   |  | Client GW        |
  | :9001            |  | GW :9002  |  | :9003            |
  | commands: [dram] |  | commands: |  | commands:         |
  |                  |  | [noval]   |  | [play, test]     |
  | Spawns locally:  |  |           |  |                  |
  | dram run job-123 |  | Spawns:   |  | Spawns:          |
  |                  |  | npx tsx   |  | npx tsx           |
  |                  |  | noval.ts  |  | play.ts           |
  +------------------+  +-----------+  +------------------+
     Server B              Server D       Server E (CI/CD)
```

Agent-Forge does not need a CLI gateway in the initial deployment because its primary interface is MCP (not CLI). Its evaluation CLI (`forge-eval`) can be added to a gateway later if needed.

### Layer 2: HTTP MCP (Remote Tool Invocation)

All MCP connections are converted from local transports to HTTP:

**Agent-Forge:** Already uses HTTP transport (`StreamableHTTPClientTransport` at `http://localhost:8001/mcp`). The only change needed is updating the URL from localhost to the cloud endpoint. No code changes, no protocol changes, no tool changes -- a one-line configuration update.

**Dramatizer:** Currently uses stdio transport (subprocess spawning). The Dramatizer adds a new `--http` flag to its existing `dram mcp` command: `dram mcp --http --port 9002`. This starts an HTTP MCP server using `mcp-go`'s `server.NewStreamableHTTPServer()` instead of `server.ServeStdio()`. All 14 existing MCP tools work unchanged -- only the transport layer changes. The mobai-agent configuration changes from:

```yaml
# Local (stdio)
dramatizer:
  command: "/Users/Clock/dramatizer/dram"
  args: ["mcp"]
  transport: "stdio"
```

to:

```yaml
# Cloud (HTTP)
dramatizer:
  url: "https://dram.moonshort.io/mcp"
  transport: "http"
```

With both MCP servers on HTTP, the agent's `mcp-client.ts` connects to all servers using the same `createHttpTransport()` code path (StreamableHTTP with SSE fallback). The stdio transport code remains in the codebase for local development but is not used in cloud deployments.

### Layer 3: Server Layer (Remote Agent Access)

The [[concepts/server-layer]] makes mobai-agent itself accessible over the network. In the local setup, the operator interacts with the agent through the terminal TUI. In the cloud deployment, the operator interacts through the web client served by the agent's HTTP server.

The same `AgentLoop` core processes messages regardless of whether they arrive through terminal stdin or WebSocket. The server layer is purely a transport change for the operator interface.

**Combined architecture:**

```
  Operator (browser)
       |
       | HTTPS / WSS
       v
  +-------------------------------+
  | mobai-agent (Server A)        |
  | :3100 HTTP + WebSocket        |
  | :3100/api/* REST API          |
  | :3100/ws   WebSocket          |
  | :3100/     Web client         |
  |                               |
  | Internal connections:         |
  |   HTTP MCP --> Agent-Forge    |
  |   HTTP MCP --> Dramatizer     |
  |   HTTP /exec --> Dram GW      |
  |   HTTP /exec --> Backend GW   |
  |   HTTP /exec --> Client GW    |
  +-------------------------------+
       |          |          |          |
       v          v          v          v
  Agent-Forge  Dramatizer  Backend    Client
  (Server C)   (Server B)  (Server D) (Server E)
  :8001 MCP    :9001 GW    :9002 GW   :9003 GW
               :9002 MCP
```

## Configuration Changes

### Local Development Configuration (config.yaml)

This is the current configuration used for local development, where all services run on one machine:

```yaml
agent:
  defaultModel: "anthropic/claude-sonnet-4.6"
  provider: "openai-compatible"
  baseUrl: "https://zenmux.ai/api/v1"
  maxOutputTokens: 8192
  contextWindow: 200000
  reservedBuffer: 20000
  maxIterations: 80

server:
  enabled: false
  port: 3100

mcp:
  servers:
    agent-forge:
      url: "http://localhost:8001/mcp"
      transport: "http"
    dramatizer:
      command: "/Users/Clock/dramatizer/dram"
      args: ["mcp"]
      transport: "stdio"

cli:
  gateways:
    # No gateways configured -- all CLI tools run locally
  localFallback: true
```

### Cloud Deployment Configuration (config.yaml)

This is the configuration for cloud deployment, where services are distributed across multiple servers:

```yaml
agent:
  defaultModel: "anthropic/claude-sonnet-4.6"
  provider: "openai-compatible"
  baseUrl: "https://zenmux.ai/api/v1"
  maxOutputTokens: 8192
  contextWindow: 200000
  reservedBuffer: 20000
  maxIterations: 80

server:
  enabled: true
  port: 3100

mcp:
  servers:
    agent-forge:
      url: "${AGENT_FORGE_MCP_URL}"        # e.g., https://forge.moonshort.io/mcp
      transport: "http"
    dramatizer:
      url: "${DRAMATIZER_MCP_URL}"          # e.g., https://dram.moonshort.io/mcp
      transport: "http"                     # Changed from stdio to http

cli:
  gateways:
    dramatizer:
      url: "${DRAMATIZER_GW_URL}"           # e.g., https://dram.moonshort.io:9001
      apiKey: "${DRAMATIZER_CLI_KEY}"
      tools: ["dram"]
      timeout: 120000
    backend:
      url: "${BACKEND_GW_URL}"              # e.g., https://backend.moonshort.io:9002
      apiKey: "${BACKEND_CLI_KEY}"
      tools: ["noval"]
      timeout: 60000
    client-test:
      url: "${CLIENT_GW_URL}"              # e.g., https://test-runner.moonshort.io:9003
      apiKey: "${CLIENT_CLI_KEY}"
      tools: ["play", "test"]
      timeout: 300000
  localFallback: true
```

### Key Differences Between Local and Cloud Configurations

| Configuration area | Local | Cloud |
|-------------------|-------|-------|
| `server.enabled` | `false` (TUI mode) | `true` (HTTP/WS mode) |
| `mcp.servers.dramatizer.transport` | `"stdio"` | `"http"` |
| `mcp.servers.dramatizer.command` | `"/Users/Clock/dramatizer/dram"` | (removed) |
| `mcp.servers.dramatizer.args` | `["mcp"]` | (removed) |
| `mcp.servers.dramatizer.url` | (not present) | `"${DRAMATIZER_MCP_URL}"` |
| `mcp.servers.agent-forge.url` | `"http://localhost:8001/mcp"` | `"${AGENT_FORGE_MCP_URL}"` |
| `cli.gateways` | Empty (no gateways) | Three gateways configured |

Environment variables (`${VAR_NAME}` syntax) are used for all cloud URLs and API keys, allowing the same configuration file to be deployed across different environments (staging, production) by changing only the environment variable values.

## What Changes vs What Does Not Change

### What Does Not Change

**CLI binaries.** The `dram` binary, the `noval.ts` entry script, the `play.ts` test runner, and all other CLI tools are completely unchanged. They do not know or care whether they are invoked by a local subprocess or by a CLI gateway. Their input is argv and environment variables; their output is stdout, stderr, and an exit code. The transport mechanism is invisible to them.

**MCP tool definitions.** All MCP tools (14 from Dramatizer, 60+ from Agent-Forge) are defined by their respective services and served through the MCP protocol. The tool names, parameter schemas, descriptions, and behaviors are unchanged. The only thing that changes is the transport over which tool calls and results are transmitted.

**Skills.** All six skill files in `skills/` (`dramatizer/pipeline.md`, `agent-forge/video-production.md`, `moonshort/game-client.md`, `general/orchestrator.md`, `general/coding.md`, `general/debugging.md`) are part of the mobai-agent codebase, deployed alongside the agent. They do not reference external service URLs or transport mechanisms. Their content remains valid regardless of deployment topology.

**Memory system.** The MEMORY.md, SOUL.md, and USER.md files, the dream cycle, and the memory consolidation system all operate on local files within the agent's deployment. They do not interact with external services and are unaffected by the transition.

**Agent's discovery loop.** The three-step progressive mastery sequence (`discover_cli` to scan tools, `cli_help` to learn usage, `cli_run` to execute) works identically. `discover_cli` now aggregates remote tools from gateways alongside local tools. `cli_help` fetches help text through whatever transport is active (local subprocess or remote gateway). `cli_run` routes transparently. The agent's learning behavior is unchanged.

**The [[concepts/four-layer-philosophy]].** All four layers (SKILL, CLI, MCP, API) work identically in the cloud deployment. SKILL documents are in the agent's local filesystem. CLI tools are accessible through gateways (or locally). MCP tools are accessible through HTTP. The bash tool still provides the API fallback. The philosophy's design principle -- the same four layers regardless of deployment topology -- is validated by this migration.

### What Changes

**config.yaml URLs.** Service URLs change from localhost to cloud endpoints. This is the primary configuration change and is handled entirely through environment variables.

**MCP transport type for Dramatizer.** Changes from `"stdio"` to `"http"`. The agent's `mcp-client.ts` already supports both transports; this is a configuration switch, not a code change.

**New gateway processes.** Each service (except Agent-Forge) deploys a CLI gateway alongside its main process. These are new processes that need to be started, monitored, and maintained.

**New server process on mobai-agent.** The agent runs in server mode instead of TUI mode, requiring the HTTP/WebSocket server to be started on a configured port.

**Network topology.** Services communicate over HTTP across the network instead of through local subprocesses and loopback connections. This introduces network latency, potential connectivity failures, and the need for TLS in production.

## Deployment Topology

### Full Deployment Diagram

```
                          Internet / VPN
                               |
                          [Reverse Proxy / LB]
                          TLS termination
                               |
         +---------------------+---------------------+
         |                                           |
    HTTPS :443                                  WSS :443
    /api/*                                      /ws
         |                                           |
         v                                           v
  +-----------------------------------------------------+
  | Server A: mobai-agent                                |
  |                                                     |
  | Processes:                                          |
  |   mobai-agent (:3100)                               |
  |     - HTTP REST API                                 |
  |     - WebSocket endpoint                            |
  |     - Static web client serving                     |
  |     - AgentLoop (reasoning, tools, memory)          |
  |                                                     |
  | Outbound connections:                               |
  |   --> Server B Dramatizer GW (:9001)    [HTTP]      |
  |   --> Server B Dramatizer MCP (:9002)   [HTTP]      |
  |   --> Server C Agent-Forge MCP (:8001)  [HTTP]      |
  |   --> Server D Backend GW (:9002)       [HTTP]      |
  |   --> Server E Client GW (:9003)        [HTTP]      |
  |   --> zenmux.ai API                     [HTTPS]     |
  |                                                     |
  | Local files:                                        |
  |   config.yaml, skills/, memory/, data/mobai.db      |
  +-----------------------------------------------------+

  +-----------------------------------------------------+
  | Server B: Dramatizer                                 |
  |                                                     |
  | Processes:                                          |
  |   dram gateway --port 9001                          |
  |     - CLI Gateway (POST /exec, GET /tools, etc.)    |
  |     - Spawns: dram <subcommand> <args>              |
  |                                                     |
  |   dram mcp --http --port 9002                       |
  |     - HTTP MCP server (StreamableHTTP)              |
  |     - 14 MCP tools                                  |
  |                                                     |
  | Local files:                                        |
  |   Dramatizer binary, job artifacts, database        |
  +-----------------------------------------------------+

  +-----------------------------------------------------+
  | Server C: Agent-Forge                                |
  |                                                     |
  | Processes:                                          |
  |   Agent-Forge main server (:8001)                   |
  |     - HTTP MCP server (StreamableHTTP)              |
  |     - 60+ MCP tools                                 |
  |     - REST API                                      |
  |                                                     |
  | Optional (if CLI access needed):                    |
  |   cli-gateway (:9001)                               |
  |     - commands: [forge-eval]                        |
  |                                                     |
  | Local files:                                        |
  |   Agent-Forge source, assets, renders               |
  +-----------------------------------------------------+

  +-----------------------------------------------------+
  | Server D: Backend                                    |
  |                                                     |
  | Processes:                                          |
  |   Backend main server (:3000)                       |
  |     - API server                                    |
  |     - Database access                               |
  |                                                     |
  |   cli-gateway (:9002)                               |
  |     - commands: [noval]                             |
  |     - Spawns: npx tsx cli/bin/noval.ts <args>       |
  |                                                     |
  | Local files:                                        |
  |   Backend source, node_modules, database            |
  +-----------------------------------------------------+

  +-----------------------------------------------------+
  | Server E: Moonshort Client (CI/CD)                   |
  |                                                     |
  | Processes:                                          |
  |   cli-gateway (:9003)                               |
  |     - commands: [play, test]                        |
  |     - Spawns: npx tsx test/play.ts <args>           |
  |     - Spawns: npx tsx test/run-tests.ts <args>      |
  |                                                     |
  | Optional:                                           |
  |   Headless browser (Chromium) for play/test         |
  |                                                     |
  | Local files:                                        |
  |   Client source, node_modules, test fixtures        |
  +-----------------------------------------------------+
```

### Port Allocation

| Server | Process | Port | Protocol |
|--------|---------|------|----------|
| A (Agent) | mobai-agent | 3100 | HTTP + WebSocket |
| B (Dramatizer) | dram gateway | 9001 | HTTP (CLI Gateway Protocol) |
| B (Dramatizer) | dram mcp --http | 9002 | HTTP (MCP StreamableHTTP) |
| C (Agent-Forge) | Main server | 8001 | HTTP (MCP StreamableHTTP + REST) |
| C (Agent-Forge) | cli-gateway (optional) | 9001 | HTTP (CLI Gateway Protocol) |
| D (Backend) | Main server | 3000 | HTTP (REST API) |
| D (Backend) | cli-gateway | 9002 | HTTP (CLI Gateway Protocol) |
| E (Client) | cli-gateway | 9003 | HTTP (CLI Gateway Protocol) |

## Migration Path

### P0: Deploy CLI Gateways (per-service, less than 1 hour each)

**Dramatizer (Go):**
1. Add `gateway.go` to `internal/cli/` (approximately 220 lines of Go code).
2. Register the `gateway` subcommand in `root.go` (2 lines changed).
3. Deploy with `dram gateway --port 9001 --api-key <generated-key>`.
4. Verify: `curl -H "Authorization: Bearer <key>" http://dram-server:9001/health` returns `{"status":"ok"}`.
5. Verify: `curl -H "Authorization: Bearer <key>" -X POST http://dram-server:9001/exec -d '{"command":"dram","args":["--version"]}' ` returns the version string.

**Backend (TypeScript):**
1. Create `cli-gateway/` directory with `server.ts`, `executor.ts`, `config.ts`, `auth.ts`, `types.ts`, `package.json`, `tsconfig.json` (approximately 315 lines total, zero npm dependencies).
2. Configure command mapping: `"noval"` maps to `spawn("npx", ["tsx", "cli/bin/noval.ts", ...])`.
3. Deploy with `npx tsx cli-gateway/server.ts` (or `bun run cli-gateway/server.ts`).
4. Verify with health check and test execution.

**Moonshort Client (TypeScript):**
1. Same directory structure as Backend.
2. Configure command mapping: `"play"` maps to the headless player, `"test"` maps to the test runner.
3. Deploy with `npx tsx cli-gateway/server.ts`.
4. Verify with health check and test execution.

### P0: Switch Dramatizer MCP to HTTP Mode (flag change)

1. Add `--http` and `--port` flags to the existing `dram mcp` command (approximately 35 lines of Go code changed in `mcp.go`).
2. When `--http` is set, use `mcp-go`'s `server.NewStreamableHTTPServer()` instead of `server.ServeStdio()`.
3. Deploy with `dram mcp --http --port 9002`.
4. Verify: connect mobai-agent's MCP client to the HTTP endpoint and confirm all 14 tools are listed.

### P1: Deploy mobai-agent Server Mode (config change)

1. Set `server.enabled: true` and `server.port: 3100` in config.yaml.
2. Set `MOBAI_API_KEY` environment variable for API authentication.
3. Start mobai-agent with `bun run dev -- --server --port 3100`.
4. Verify: `curl -H "Authorization: Bearer <key>" http://agent-server:3100/api/health` returns status ok with tool count and active skills.
5. Verify: Open web client at `http://agent-server:3100/` and confirm WebSocket connection.

### P1: Update config.yaml URLs Per Environment (env vars)

1. Replace all hardcoded localhost URLs with environment variable references.
2. Change Dramatizer MCP from stdio to HTTP transport.
3. Add CLI gateway configurations for all three gateways.
4. Set environment variables (`DRAMATIZER_MCP_URL`, `AGENT_FORGE_MCP_URL`, `DRAMATIZER_GW_URL`, `BACKEND_GW_URL`, `CLIENT_GW_URL`, and corresponding `_CLI_KEY` variables) per deployment environment.
5. Verify: restart mobai-agent and confirm all MCP servers connect and all CLI gateways are reachable via `discover_cli`.

### P2: Build and Deploy Web Client (one-time build)

1. Run `cd web && npm install && npm run build` to produce `web/dist/`.
2. Include `web/dist/` in the mobai-agent deployment artifact.
3. Verify: access the web client at the agent's URL and confirm the full chat workflow (create session, send message, receive streaming response, view tool progress).

### P2: Set Up Reverse Proxy and TLS for Production

1. Deploy a reverse proxy (nginx, Caddy, or cloud load balancer) in front of mobai-agent.
2. Configure TLS termination for HTTPS and WSS.
3. Proxy `/api/*` and `/ws` to mobai-agent's HTTP server.
4. Proxy `/` and static paths to the web client (or let mobai-agent serve them directly).
5. Optionally configure separate TLS-terminated endpoints for each CLI gateway and MCP server.
6. Verify: access the web client over HTTPS with WSS WebSocket connection.

### P3: Multi-User Support (session isolation, auth)

1. Add WebSocket authentication (token verification on upgrade).
2. Implement per-user session isolation (users see only their own sessions).
3. Add user management (create user, assign API key, configure permissions).
4. Add rate limiting per user.
5. This phase is not required for initial cloud deployment (single-user is sufficient) but is necessary for production multi-user access.

## Security Considerations

### Internal Network Only

CLI gateways are not exposed to the public internet. They run on internal network interfaces accessible only from within the deployment's private network. The only externally-accessible endpoint is the reverse proxy fronting mobai-agent's server layer. All gateway-to-gateway and agent-to-gateway communication occurs over the internal network.

### Bearer Token Authentication on All Gateways

Every CLI gateway requires a Bearer token (`CLI_GATEWAY_KEY` environment variable) for all requests. Each gateway has its own unique key. The corresponding keys are configured in mobai-agent's `config.yaml` under `cli.gateways.<name>.apiKey`. Compromising one gateway's key does not grant access to other gateways.

The mobai-agent server itself requires a separate Bearer token (`MOBAI_API_KEY` environment variable) for its REST API. WebSocket connections do not currently require authentication (planned for P3 multi-user support).

### TLS Between Services in Production

In production deployments, all inter-service communication should use TLS (HTTPS instead of HTTP). This prevents eavesdropping on CLI command output, MCP tool call parameters and results, and API keys transmitted in Authorization headers. The reverse proxy handles TLS termination for external traffic. Internal service-to-service TLS can be implemented through mutual TLS (mTLS) or through a service mesh.

### mobai-agent API Key for Server Access

The `MOBAI_API_KEY` controls access to the agent's REST API. Without a valid key, external clients cannot create sessions, send messages, read memory, or activate skills. The web client, when served from the same origin as the API, can include the key in its requests (configured at build time or through a login flow).

### No Shell Expansion in Any Gateway

As documented in the [[concepts/cli-gateway-protocol]], all gateways execute commands via direct process spawning (no `sh -c`), preventing shell injection. This security property is maintained regardless of deployment topology.

## Related

- [[entities/cli-gateway]]
- [[concepts/cli-gateway-protocol]]
- [[concepts/server-layer]]
- [[concepts/four-layer-philosophy]]
- [[entities/mobai-agent]]
- [[entities/dramatizer]]
- [[entities/agent-forge]]

## Sources

- [CLI Gateway + Server Layer Design Spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
