---
title: CLI Gateway
tags: [microservice, http, cli, cloud, deployment, protocol]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md, raw/2026-04-14-mobai-agent-memory.md]
created: 2026-04-14
updated: 2026-04-14
---

Lightweight HTTP microservice deployed alongside each Moonshort platform service. Enables remote CLI command execution while preserving the full CLI experience -- progressive discovery, help caching, and self-correction all work identically whether commands execute locally or remotely. The gateway is the key infrastructure piece that allows [[entities/mobai-agent]] to control distributed services as if they were local.

## Purpose

In local development, all platform services run on the same machine and the agent can execute CLI tools directly via `Bun.spawn`. In cloud deployments, services run on different servers. The CLI Gateway bridges this gap by exposing a thin HTTP wrapper around CLI commands. The agent's `cli_run` tool transparently routes commands to the appropriate gateway based on configuration, making remote execution invisible to the LLM.

This preserves the [[concepts/four-layer-philosophy]] design: the agent continues to use progressive discovery (`discover_cli` -> `cli_help` -> `cli_run`) regardless of where the actual binary runs.

## All 4 Deployments

### Dramatizer Gateway (Go Implementation)

- **Project:** [[entities/dramatizer]]
- **Implementation:** Go subcommand `dram gateway`, added to the existing Cobra CLI
- **Source file:** `internal/cli/gateway.go` (~220 lines)
- **Integration:** Modified `internal/cli/root.go` to add `rootCmd.AddCommand(gatewayCmd)`
- **Router:** Chi v5.2.5 (already in go.mod for the REST API)
- **Port:** 9001 (default, configurable via `--port` flag)
- **Command:** `dram gateway --port 9001 --api-key <key>` or `dram gateway --port 9001` (reads `CLI_GATEWAY_KEY` env var)
- **Allowlist:** Hardcoded `["dram"]` -- only allows executing `dram` subcommands
- **Execution model:** The gateway spawns `dram <args...>` by self-referencing the binary via `os.Executable()`. This means the gateway process spawns new instances of itself to handle each command, inheriting the same binary path and environment. `exec.CommandContext()` is used with a context-based timeout for automatic process termination.
- **Middleware chain:** Chi router with bearer auth middleware -> command validation -> execution handler

### Agent-Forge Gateway (TypeScript Implementation)

- **Project:** [[entities/agent-forge]]
- **Implementation:** TypeScript microservice in `cli-gateway/` directory
- **Source files:** `server.ts`, `executor.ts`, `config.ts`, `auth.ts`, `types.ts`
- **Runtime:** Node.js (zero external npm dependencies -- uses built-in `http`, `child_process`, `readline`)
- **Port:** 9001 (default)
- **Command:** `npx tsx cli-gateway/server.ts` or `bun run cli-gateway/server.ts`
- **Command mapping:**

| Short Name | Binary | Base Args | Description |
|-----------|--------|-----------|-------------|
| `forge-eval` | `npx` | `["tsx", "cli/src/main.ts"]` | Agent-Forge evaluation CLI |

- **Working directory:** `process.cwd()` (the Agent-Forge project root)

### Backend Gateway (TypeScript Implementation)

- **Project:** [[entities/moonshort-backend]]
- **Implementation:** Identical TypeScript gateway structure in `cli-gateway/` directory
- **Source files:** Same 7-file structure as Agent-Forge gateway
- **Port:** 9002 (default)
- **Command:** `npx tsx cli-gateway/server.ts`
- **Command mapping:**

| Short Name | Binary | Base Args | Description |
|-----------|--------|-----------|-------------|
| `noval` | `npx` | `["tsx", "cli/bin/noval.ts"]` | Moonshort game CLI |

- **Working directory:** `process.cwd()` (the backend project root)

### Moonshort Client Gateway (TypeScript Implementation)

- **Project:** [[entities/moonshort-client]]
- **Implementation:** Identical TypeScript gateway structure in `cli-gateway/` directory
- **Source files:** Same 7-file structure as Agent-Forge gateway
- **Port:** 9003 (default)
- **Command:** `npx tsx cli-gateway/server.ts`
- **Command mapping:**

| Short Name | Binary | Base Args | Description |
|-----------|--------|-----------|-------------|
| `play` | `npx` | `["tsx", "--tsconfig", "test/tsconfig.test.json", "test/play.ts"]` | Headless AutoPlayer |
| `test` | `npx` | `["tsx", "--tsconfig", "test/tsconfig.test.json", "test/run-tests.ts"]` | Test suite runner |

- **Working directory:** `process.cwd()` (the moonshort project root)

## Full HTTP Protocol

All four gateways implement the identical HTTP API contract. See also [[concepts/cli-gateway-protocol]] for the formal specification.

### Endpoint 1: POST /exec (Synchronous Execution)

Executes a CLI command and returns the complete output after the process finishes.

**Request:**
```json
{
  "command": "dram",
  "args": ["run", "job-123", "--stage", "ludify"],
  "timeout": 30000,
  "cwd": "/optional/working/directory",
  "env": { "OPTIONAL_ENV_VAR": "value" }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `command` | string | yes | -- | CLI tool name (must be in the allowlist) |
| `args` | string[] | yes | -- | Command arguments as an array |
| `timeout` | number | no | 30000 | Timeout in milliseconds |
| `cwd` | string | no | gateway default | Working directory override |
| `env` | Record<string, string> | no | {} | Additional environment variables |

**Response (200 -- command completed, even with non-zero exit code):**
```json
{
  "stdout": "Processing stage ludify...\nDone.",
  "stderr": "",
  "exitCode": 0,
  "durationMs": 4521
}
```

| Field | Type | Description |
|-------|------|-------------|
| `stdout` | string | Standard output from the process |
| `stderr` | string | Standard error from the process |
| `exitCode` | number | Process exit code (0 = success) |
| `durationMs` | number | Total execution time in milliseconds |

**Error responses:**
- `400` -- Command not in the allowlist, or args contain forbidden characters
- `403` -- Authentication failure (missing or invalid Bearer token)
- `408` -- Timeout exceeded (process was killed)

### Endpoint 2: POST /exec/stream (SSE Streaming Execution)

Executes a CLI command with real-time output streaming via Server-Sent Events.

**Request:** Same JSON body as `POST /exec`.

**Response:** SSE event stream with three event types:

**`stdout` event** -- A line of standard output:
```
event: stdout
data: {"line": "Processing stage ludify..."}
```

**`stderr` event** -- A line of standard error:
```
event: stderr
data: {"line": "warning: deprecated flag"}
```

**`exit` event** -- Process termination (always the final event):
```
event: exit
data: {"exitCode": 0, "durationMs": 4521}
```

The SSE stream uses `bufio.Scanner` (Go) or `readline` (TypeScript) on the process stdout and stderr pipes, emitting each line as it becomes available. This enables real-time progress monitoring for long-running commands like pipeline execution.

### Endpoint 3: GET /tools (Tool Discovery)

Returns the list of CLI tools available on this gateway.

**Response:**
```json
{
  "tools": [
    {
      "name": "dram",
      "description": "Dramatizer CLI",
      "version": "0.3.2"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Short command name |
| `description` | string | yes | Human-readable description |
| `version` | string | no | Tool version string |

This endpoint is called by [[entities/mobai-agent]]'s `discover_cli` tool to aggregate available commands across all configured gateways.

### Endpoint 4: GET /health (Health Check)

Returns gateway status.

**Response:**
```json
{
  "status": "ok",
  "uptime": 3600
}
```

## Command Mapping Mechanism

Each gateway maintains a command mapping configuration that translates short command names into actual executable commands with base arguments.

When the gateway receives a `POST /exec` request with `{ command: "noval", args: ["play", "25", "--auto"] }`, the execution flow is:

1. **Lookup:** Find `"noval"` in the command map. Result: `{ bin: "npx", baseArgs: ["tsx", "cli/bin/noval.ts"] }`
2. **Merge arguments:** Concatenate `baseArgs` with the request `args`: `["tsx", "cli/bin/noval.ts", "play", "25", "--auto"]`
3. **Spawn:** Execute `spawn("npx", mergedArgs, { cwd: configuredCwd, env: mergedEnv, timeout: requestTimeout })`
4. **Capture:** Collect stdout and stderr until the process exits
5. **Return:** Send `{ stdout, stderr, exitCode, durationMs }` to the client

This mapping mechanism means the gateway caller does not need to know the actual binary path, base arguments, or working directory. It just says "run noval with these args" and the gateway resolves everything.

## Security Model

### Authentication

All endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <api-key>
```

The API key is sourced from the `CLI_GATEWAY_KEY` environment variable, or the `--api-key` CLI flag for the Go implementation. Requests without a valid token receive a 403 response.

### Command Allowlist

Only commands explicitly configured in the command mapping are executable. If a request specifies a command that is not in the allowlist, the gateway returns a 400 error without executing anything. There is no wildcard or pattern-based matching -- the command must be an exact match.

### No Shell Expansion

Commands are executed via `spawn` (Node.js `child_process.spawn`) or `exec.CommandContext` (Go) directly, never through a shell (`sh -c`). This prevents shell injection attacks because:
- No shell metacharacter interpretation
- No environment variable expansion in arguments
- No glob expansion
- No command chaining

### Argument Injection Filtering

Arguments are scanned for dangerous characters before execution. The following characters cause the request to be rejected with a 400 error:

| Character | Reason |
|-----------|--------|
| `;` | Command chaining |
| `\|` | Pipe to another command |
| `` ` `` | Command substitution (backtick) |
| `$()` | Command substitution (subshell) |
| `&&` | Conditional execution (AND) |
| `\|\|` | Conditional execution (OR) |

This filtering is a defense-in-depth measure. Since commands are not executed through a shell, these characters would not have their shell meaning anyway. But the filtering catches cases where arguments might be passed to subprocesses that do use shell interpretation.

### Timeout Enforcement

Each request has a timeout (default 30000ms, configurable per request). If the process exceeds the timeout:

1. The process receives a SIGTERM signal
2. If it does not exit within a grace period, SIGKILL is sent
3. The gateway returns a 408 (Request Timeout) response
4. Stdout and stderr collected before the timeout are discarded

## TypeScript Implementation Architecture

The three TypeScript gateways (Agent-Forge, Backend, Moonshort Client) share identical code with project-specific configuration.

### Directory Structure

```
cli-gateway/
  server.ts        # HTTP server entry point
  executor.ts      # Command spawner with timeout, streaming, and security
  config.ts        # Project-specific: allowlist, command mapping, port
  auth.ts          # Bearer token verification middleware
  types.ts         # Shared TypeScript types (CliExecRequest, CliExecResponse)
  package.json     # Zero external dependencies
  tsconfig.json    # Standalone TypeScript configuration
```

### File Roles

**`server.ts`** -- Creates a Node.js HTTP server using the built-in `http` module. Routes incoming requests to the appropriate handler based on method and path. Handles CORS headers. Calls `auth.ts` for authentication on all routes. Parses JSON request bodies and sends JSON responses.

**`executor.ts`** -- The core execution engine. Receives a validated `CliExecRequest`, looks up the command in the mapping, builds the full argument list, spawns the process via `child_process.spawn`, manages timeout with `setTimeout` and process kill, collects stdout/stderr via pipe streams, and returns a `CliExecResponse`. For streaming mode, it uses `readline.createInterface` on the process output pipes and emits SSE events through the HTTP response.

**`config.ts`** -- Project-specific configuration. Defines the port number and the command mapping object. This is the only file that differs between the three TypeScript gateways. Each project defines its own commands with the appropriate binary path, base arguments, working directory, and description.

**`auth.ts`** -- Reads the `CLI_GATEWAY_KEY` environment variable on startup. Provides a `verifyAuth(req)` function that extracts the Bearer token from the Authorization header and compares it against the stored key. Returns true/false.

**`types.ts`** -- TypeScript type definitions shared across all files: `CliExecRequest` (command, args, timeout, cwd, env), `CliExecResponse` (stdout, stderr, exitCode, durationMs), `CliToolInfo` (name, description, version), and `CommandMapping` (bin, baseArgs, cwd, description).

### Runtime

The TypeScript gateway uses zero external npm dependencies. It relies entirely on Node.js built-in APIs: `http` for the server, `child_process` for process spawning, and `readline` for streaming line-by-line output. This means:
- No `npm install` required
- Entry via `npx tsx cli-gateway/server.ts` (uses tsx for TypeScript execution)
- Can also run with Bun: `bun run cli-gateway/server.ts`

## Go Implementation Architecture

The Dramatizer gateway is implemented in Go as a Cobra subcommand integrated into the existing `dram` binary.

### File: `internal/cli/gateway.go` (~220 lines)

Contains:
- The `gatewayCmd` Cobra command definition with `--port` and `--api-key` flags
- Chi router setup with bearer auth middleware
- Handler functions for all 4 endpoints (`/exec`, `/exec/stream`, `/tools`, `/health`)
- The execution engine using `exec.CommandContext()` for timeout management
- SSE streaming using `bufio.Scanner` on stdout/stderr pipes
- Self-referencing binary execution via `os.Executable()`

### Integration: `internal/cli/root.go`

Two lines added: `import` and `rootCmd.AddCommand(gatewayCmd)`. The gateway is just another subcommand alongside `mcp`, `serve`, `run`, etc.

### Chi Router Middleware Chain

```
Request -> Bearer Auth Middleware -> Command Validation -> Execution Handler -> Response
```

The middleware chain ensures authentication is checked before any request processing, and command validation happens before any process spawning.

## Deployment

Each gateway runs as an independent process with its own port. Gateways can be deployed on the same server as the service they wrap, or on dedicated gateway servers. In production:

- Dramatizer Gateway runs alongside the `dram` binary on the same server
- Agent-Forge Gateway runs alongside the Next.js Agent-Forge server
- Backend Gateway runs alongside the Next.js Backend server
- Client Gateway runs alongside the test infrastructure

Each gateway only needs:
1. The service binary/source code to be available
2. The `CLI_GATEWAY_KEY` environment variable set
3. Network accessibility from [[entities/mobai-agent]]

## Relationship to mobai-agent

### Configuration

[[entities/mobai-agent]]'s `config.yaml` contains the `cli.gateways` section that maps gateway names to URLs:

```yaml
cli:
  gateways:
    dramatizer:
      url: "http://dramatizer.internal:9001"
      apiKey: "${DRAMATIZER_CLI_KEY}"
      tools: ["dram"]
      timeout: 120000
    backend:
      url: "http://backend.internal:9002"
      apiKey: "${BACKEND_CLI_KEY}"
      tools: ["noval"]
    client-test:
      url: "http://test-runner.internal:9003"
      apiKey: "${CLIENT_CLI_KEY}"
      tools: ["play", "test"]
  localFallback: true
```

### findGateway() Routing

When the agent calls `cli_run` with a command name, the `findGateway()` function in `src/tool/cli-gateway-client.ts` iterates through all configured gateways and checks if the command name appears in the gateway's `tools` array. The first match is used. If no match is found and `localFallback` is true, the command executes locally.

### discover_cli Aggregation

When the agent calls `discover_cli` without a specific command name, the tool queries all configured gateways' `/tools` endpoints in parallel and merges the results with locally-discovered CLIs. The output groups tools by source:

```
Found 8 CLI tools:

[Remote Gateways]
  dram (0.3.2) [remote: dramatizer]
  noval [remote: backend]
  play [remote: client-test]
  test [remote: client-test]

[Local]
  git (2.43.0)
  docker (24.0.7)
  node (20.11.0)
  bun (1.0.25)
```

### Transparency

The entire gateway mechanism is invisible to the LLM agent. The agent uses the same three-step progressive discovery pattern regardless of execution location:

1. `discover_cli` -- "What CLIs are available?" (includes remote tools)
2. `cli_help` -- "How do I use this CLI?" (help text fetched via gateway or locally)
3. `cli_run` -- "Execute this command" (routed to gateway or local spawn)

The agent never sees gateway URLs, authentication tokens, or remote/local distinctions. From its perspective, it simply has a set of CLI tools it can discover, learn about, and execute.

## Related

- [[concepts/cli-gateway-protocol]] -- Formal HTTP API specification for the gateway protocol
- [[concepts/four-layer-philosophy]] -- Design framework that positions CLI gateways in the architecture
- [[entities/mobai-agent]] -- Orchestrator agent that routes commands through gateways
- [[entities/dramatizer]] -- Go implementation of the gateway as `dram gateway`
- [[entities/agent-forge]] -- TypeScript gateway wrapping `forge-eval`
- [[entities/moonshort-backend]] -- TypeScript gateway wrapping `noval`
- [[entities/moonshort-client]] -- TypeScript gateway wrapping `play` and `test`
- [[syntheses/cloud-deployment-architecture]] -- How gateways fit into the cloud deployment topology

## Sources

- [Design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
