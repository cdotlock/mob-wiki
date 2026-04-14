---
title: CLI Gateway Protocol
tags: [protocol, http, cli, microservice]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

Unified HTTP protocol implemented by all [[entities/cli-gateway]] instances across the Moonshort platform. Enables remote CLI command execution while preserving the CLI's progressive discovery characteristics.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/exec` | Execute CLI command synchronously |
| `POST` | `/exec/stream` | Execute with SSE streaming output |
| `GET` | `/tools` | List available CLI tools |
| `GET` | `/health` | Health check |

## Request: POST /exec

```json
{
  "command": "dram",
  "args": ["run", "job-123", "--stage", "ludify"],
  "timeout": 60000,
  "cwd": "/optional/workdir",
  "env": { "DEBUG": "true" }
}
```

## Response: POST /exec

```json
{
  "stdout": "Processing stage ludify...\nDone.",
  "stderr": "",
  "exitCode": 0,
  "durationMs": 4521
}
```

HTTP 200 for all completed executions (even non-zero exit code). 408 for timeout. 403 for auth failure. 400 for disallowed command.

## Response: POST /exec/stream

SSE event stream for long-running commands:

```
event: stdout
data: {"line": "Processing stage ludify..."}

event: stderr
data: {"line": "warning: deprecated flag"}

event: exit
data: {"exitCode": 0, "durationMs": 4521}
```

## Command Mapping

Gateways map short command names to actual executables. Example:

```
"noval" --> spawn("npx", ["tsx", "cli/bin/noval.ts", ...userArgs])
"play"  --> spawn("npx", ["tsx", "test/play.ts", ...userArgs])
```

The gateway resolves the real binary and base arguments, appends user-provided args.

## Security Model

- Bearer token: `Authorization: Bearer <key>` (from `CLI_GATEWAY_KEY` env)
- Allowlist: only configured commands are executable
- No shell: `spawn()` / `exec.CommandContext()` directly (no `sh -c`)
- Injection filtering: args containing `;`, `|`, backtick, `$()`, `&&`, `||` are rejected

## Design Rationale

CLI binaries remain unchanged. The gateway is purely a transport layer. This means:
- [[concepts/four-layer-philosophy]]'s CLI layer works identically local or remote
- Progressive discovery (`--help`) works via gateway
- Self-correction loops work transparently
- No code changes needed in any CLI tool

## Related

- [[entities/cli-gateway]]
- [[concepts/four-layer-philosophy]]
- [[syntheses/cloud-deployment-architecture]]

## Sources

- [Design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
