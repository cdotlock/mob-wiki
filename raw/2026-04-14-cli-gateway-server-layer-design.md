# CLI Gateway + Server Layer Design Spec

**Date:** 2026-04-14
**Scope:** 5 repos, 8 commits, 5 new branches

## Overview

Enable the Moonshort platform to run in distributed cloud environments by:
1. Adding CLI Gateway microservices to all 4 platform projects
2. Adding HTTP MCP mode to Dramatizer
3. Completing mobai-agent's HTTP/WebSocket server layer + lightweight web client
4. Integrating CLI routing in mobai-agent to transparently proxy CLI commands to remote gateways

## Branch & Commit Plan

| Repo | Path | Base Branch | New Branch | Commits |
|------|------|-------------|------------|---------|
| Dramatizer | `/Users/Clock/dramatizer/` | `claude/go-rewrite` | `feat/cli-gateway` | 1. `dram gateway` subcommand 2. `dram mcp --http` mode |
| Agent-Forge | `/Users/Clock/video-loop/Agent-Forge/` | `main` | `feat/cli-gateway` | 1. CLI Gateway microservice |
| Backend | `/Users/Clock/moonshort backend/backend/` | `main` | `feat/cli-gateway` | 1. CLI Gateway microservice |
| Moonshort Client | `/Users/Clock/moonshort backend/moonshort/` | `main` | `feat/cli-gateway` | 1. CLI Gateway microservice |
| mobai-agent | `/Users/Clock/moonshort backend/mobai-agent/` | `main` | `feat/server-layer` | 1. HTTP/WS server layer 2. Web client 3. CLI routing integration |

---

## Part 1: CLI Gateway Unified Protocol

All four gateways implement the same HTTP API contract.

### Endpoints

```
POST /exec           Execute CLI command synchronously
POST /exec/stream    Execute CLI command with SSE streaming output
GET  /tools          List available CLI tools on this server
GET  /health         Health check
```

### Request: POST /exec

```typescript
interface CliExecRequest {
  command: string;        // "dram", "noval", "play", etc.
  args: string[];         // ["run", "job-123", "--stage", "ludify"]
  timeout?: number;       // ms, default 30000
  cwd?: string;           // override working directory
  env?: Record<string, string>; // additional env vars
}
```

### Response: POST /exec

```typescript
interface CliExecResponse {
  stdout: string;
  stderr: string;
  exitCode: number;
  durationMs: number;
}
```

HTTP status: 200 for all completed executions (even non-zero exit code). 408 for timeout. 403 for auth failure. 400 for disallowed command.

### Response: POST /exec/stream

SSE event stream:
```
event: stdout
data: {"line": "Processing stage ludify..."}

event: stderr
data: {"line": "warning: deprecated flag"}

event: exit
data: {"exitCode": 0, "durationMs": 4521}
```

### Response: GET /tools

```typescript
interface CliToolsResponse {
  tools: Array<{
    name: string;         // "dram"
    description: string;  // "Dramatizer CLI"
    version?: string;     // "0.3.2"
  }>;
}
```

### Security

- **Authentication:** `Authorization: Bearer <api-key>` header on all requests
- **Command allowlist:** Only configured commands are executable. Requests for unlisted commands return 400.
- **No shell expansion:** Commands executed via `spawn`/`exec.Command` directly (no `sh -c`). Prevents shell injection.
- **Argument filtering:** Args containing `;`, `|`, `` ` ``, `$()`, `&&`, `||` are rejected.
- **Timeout enforcement:** Process killed after timeout, returns 408.
- **API key source:** Environment variable `CLI_GATEWAY_KEY` or `--api-key` flag.

---

## Part 2: Dramatizer — `dram gateway` (Go)

### New File: `internal/cli/gateway.go`

Adds `gateway` subcommand to existing cobra CLI. Reuses chi router (already in go.mod).

```
dram gateway --port 9001 --api-key <key>
dram gateway --port 9001  # reads CLI_GATEWAY_KEY env var
```

**Flags:**
- `--port` (int, default 9001)
- `--api-key` (string, default from env `CLI_GATEWAY_KEY`)

**Implementation details:**
- chi.NewRouter() with bearer auth middleware
- `POST /exec` handler: `exec.CommandContext()` with timeout, capture stdout/stderr
- `POST /exec/stream` handler: line-by-line SSE via `bufio.Scanner` on stdout/stderr pipes
- `GET /tools` handler: returns `[{ name: "dram", description: "Dramatizer CLI", version: version }]`
- `GET /health` handler: returns `{ status: "ok", uptime: ... }`
- Allowlist: hardcoded `["dram"]` — only allows executing `dram` subcommands
- Execution: spawns `dram <args...>` (self-referencing binary) or the configured binary path
- CWD: defaults to the dramatizer project root

**Files to create/modify:**
- CREATE `internal/cli/gateway.go` (~200 lines)
- MODIFY `internal/cli/root.go` — add `rootCmd.AddCommand(gatewayCmd)`

---

## Part 3: Dramatizer — HTTP MCP Mode

### Modified File: `internal/cli/mcp.go`

Add `--http` and `--port` flags to existing `mcp` command.

```
dram mcp                          # stdio mode (unchanged)
dram mcp --http --port 9002       # HTTP StreamableHTTP mode (new)
```

**Implementation:**
- When `--http` flag is set, use `mcp-go`'s HTTP transport instead of `server.ServeStdio()`
- The `mcp-go` library (v0.46.0) supports `server.NewStreamableHTTPServer()` for HTTP transport
- All 14 existing MCP tools work unchanged — only the transport layer changes

**Files to modify:**
- MODIFY `internal/cli/mcp.go` — add flags + HTTP branch (~30 lines added)

---

## Part 4: TS CLI Gateway (Agent-Forge / Backend / Moonshort Client)

Three projects share identical gateway core code with project-specific config.

### Directory Structure (in each project)

```
cli-gateway/
├── server.ts          # HTTP server entry point
├── executor.ts        # Command spawner (timeout, streaming, security)
├── config.ts          # Project-specific: allowlist, command mapping, port
├── auth.ts            # Bearer token middleware
├── types.ts           # Shared types (CliExecRequest, CliExecResponse)
├── package.json       # Zero external deps (uses Node built-in APIs)
├── tsconfig.json      # Standalone TS config
└── README.md          # Usage instructions
```

### Runtime

- Uses Node.js built-in APIs only: `http`, `child_process`, `readline`
- No external dependencies (zero npm install)
- Entry: `npx tsx cli-gateway/server.ts` or `node --import tsx cli-gateway/server.ts`
- Can also run with Bun: `bun run cli-gateway/server.ts`

### Command Mapping

Each project maps short command names to actual executables:

**Agent-Forge (`cli-gateway/config.ts`):**
```typescript
export const CONFIG = {
  port: 9001,
  commands: {
    "forge-eval": {
      bin: "npx",
      baseArgs: ["tsx", "cli/src/main.ts"],
      cwd: process.cwd(),
      description: "Agent-Forge eval CLI",
    },
  },
};
```

**Backend (`cli-gateway/config.ts`):**
```typescript
export const CONFIG = {
  port: 9002,
  commands: {
    "noval": {
      bin: "npx",
      baseArgs: ["tsx", "cli/bin/noval.ts"],
      cwd: process.cwd(),
      description: "Moonshort game CLI",
    },
  },
};
```

**Moonshort Client (`cli-gateway/config.ts`):**
```typescript
export const CONFIG = {
  port: 9003,
  commands: {
    "play": {
      bin: "npx",
      baseArgs: ["tsx", "--tsconfig", "test/tsconfig.test.json", "test/play.ts"],
      cwd: process.cwd(),
      description: "Headless AutoPlayer",
    },
    "test": {
      bin: "npx",
      baseArgs: ["tsx", "--tsconfig", "test/tsconfig.test.json", "test/run-tests.ts"],
      cwd: process.cwd(),
      description: "Test suite runner",
    },
  },
};
```

### Execution Model

When gateway receives `POST /exec { command: "noval", args: ["play", "25", "--auto"] }`:

1. Look up "noval" in command map → `{ bin: "npx", baseArgs: ["tsx", "cli/bin/noval.ts"] }`
2. Build full args: `["tsx", "cli/bin/noval.ts", "play", "25", "--auto"]`
3. `spawn("npx", fullArgs, { cwd, env, timeout })`
4. Capture stdout/stderr, return `{ stdout, stderr, exitCode, durationMs }`

---

## Part 5: mobai-agent — HTTP/WebSocket Server Layer

### New Files

```
src/server/
├── http.ts            # Main HTTP + WebSocket server
├── routes.ts          # REST API route handlers
├── ws-handler.ts      # WebSocket message handling
├── auth.ts            # API key authentication
└── types.ts           # (existing, extend with server types)
```

### Entry Point Change

`src/index.ts` gains a new mode: when `config.server.enabled = true`, start HTTP server instead of (or alongside) TUI.

```
bun run dev                          # TUI mode (unchanged)
bun run dev -- --server              # Server mode (new)
bun run dev -- --server --port 3100  # Server mode with custom port
```

### REST API

All endpoints prefixed with `/api/`. Authentication via `Authorization: Bearer <key>`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check + connected MCP status |
| `POST` | `/api/sessions` | Create new session, returns `{ sessionId }` |
| `GET` | `/api/sessions` | List all sessions |
| `GET` | `/api/sessions/:id` | Get session details + message history |
| `DELETE` | `/api/sessions/:id` | End session |
| `POST` | `/api/sessions/:id/message` | Send message (non-streaming, returns full response) |
| `GET` | `/api/skills` | List all skills with activation status |
| `POST` | `/api/skills/:name/activate` | Activate a skill |
| `GET` | `/api/memory/:type` | Read MEMORY.md / SOUL.md / USER.md |

### WebSocket `/ws`

Bidirectional streaming for real-time chat.

**Client → Server messages:**
```typescript
// Send a chat message
{ type: "message", sessionId: string, content: string }

// Create session
{ type: "create_session", title?: string }

// End session
{ type: "end_session", sessionId: string }
```

**Server → Client messages:**
```typescript
// Session created
{ type: "session_created", sessionId: string }

// Streaming assistant text (incremental)
{ type: "text", content: string }

// Tool execution progress
{ type: "tool_progress", toolName: string, status: "running" | "done" | "error", result?: string }

// Thinking text
{ type: "thinking", content: string }

// Response complete
{ type: "done", usage: { promptTokens: number, completionTokens: number } }

// Error
{ type: "error", message: string }
```

### Implementation

Uses Bun's built-in `Bun.serve()` with WebSocket support:

```typescript
Bun.serve({
  port: config.server.port,
  fetch(req, server) {
    // Upgrade WebSocket
    if (new URL(req.url).pathname === "/ws") {
      server.upgrade(req);
      return;
    }
    // REST API routing
    return handleRequest(req);
  },
  websocket: {
    open(ws) { /* register client */ },
    message(ws, data) { /* dispatch to AgentLoop */ },
    close(ws) { /* cleanup */ },
  },
});
```

The server creates an `AgentLoop` instance (same as TUI mode) and forwards WebSocket messages to `loop.handleMessage()`, streaming callbacks back to the client.

### Static File Serving

`GET /` and `GET /*` (non-API paths) serve from `web/dist/`. Enables the web client to be served from the same port.

---

## Part 6: mobai-agent — Lightweight Web Client

### Directory Structure

```
web/
├── index.html
├── package.json        # vite, react, tailwindcss, react-markdown
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx        # Entry point
│   ├── App.tsx         # Main layout (sidebar + chat area)
│   ├── components/
│   │   ├── ChatView.tsx    # Message list with markdown rendering
│   │   ├── InputBar.tsx    # Text input + send button
│   │   ├── ToolStatus.tsx  # Active tool execution indicators
│   │   ├── MessageBubble.tsx # Single message (user/assistant/tool)
│   │   └── SessionList.tsx # Simple session selector (sidebar)
│   ├── hooks/
│   │   └── useWebSocket.ts # WebSocket connection + reconnect
│   ├── types.ts        # WS message types
│   └── styles.css      # Tailwind base
└── dist/               # Build output (served by server)
```

### UI Layout

```
┌─────────────────────────────────────────────┐
│  mobai-agent                    [session ▼]  │
├────────┬────────────────────────────────────┤
│Sessions│  Messages                          │
│        │  ┌─────────────────────────────┐   │
│ > s1   │  │ [user] 帮我跑一下 dram...    │   │
│   s2   │  │                             │   │
│   s3   │  │ [assistant] 正在执行...      │   │
│        │  │   ⚙ cli_run: running        │   │
│        │  │                             │   │
│        │  │ [assistant] 完成了，结果...   │   │
│        │  └─────────────────────────────┘   │
│        │                                    │
│        │  ┌──────────────────────┐ [Send]   │
│        │  │ 输入消息...           │          │
│        │  └──────────────────────┘          │
└────────┴────────────────────────────────────┘
```

### Build & Serve

```bash
cd web && npm install && npm run build   # → web/dist/
# Server auto-serves web/dist/ at GET /
```

Development mode: `cd web && npm run dev` (Vite dev server with proxy to API).

---

## Part 7: mobai-agent — CLI Routing Integration

### Config Change

`config.yaml` gains `cli.gateways` section:

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

### Code Changes

**`src/config/schema.ts`** — Add `cli` section to Zod schema:

```typescript
const cliGatewaySchema = z.object({
  url: z.string(),
  apiKey: z.string().optional(),
  tools: z.array(z.string()),
  timeout: z.number().default(30000),
});

const cliSchema = z.object({
  gateways: z.record(z.string(), cliGatewaySchema).default({}),
  localFallback: z.boolean().default(true),
});
```

**`src/tool/cli-gateway-client.ts`** — New file, HTTP client for remote gateways:

```typescript
export async function execRemoteCli(
  gatewayUrl: string,
  apiKey: string,
  request: CliExecRequest,
): Promise<CliExecResponse> {
  const res = await fetch(`${gatewayUrl}/exec`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${apiKey}`,
    },
    body: JSON.stringify(request),
  });
  return res.json();
}
```

**`src/tool/builtin/cli-run.ts`** — Add routing logic:

```typescript
// Before executing locally, check if command matches a gateway
const gateway = findGateway(command, gateways);
if (gateway) {
  const result = await execRemoteCli(gateway.url, gateway.apiKey, { command, args, timeout });
  if (result.exitCode !== 0) throw new ToolError(...);
  return result.stdout;
}
// Fallback: local execution (existing code)
```

**`src/tool/builtin/discover-cli.ts`** — Aggregate remote + local tools:

```typescript
// Fetch tools from all gateways in parallel
const remoteTools = await Promise.all(
  gateways.map(gw => fetch(`${gw.url}/tools`).then(r => r.json()))
);
// Merge with local scan
return [...remoteTools.flat(), ...localTools];
```

---

## File Change Summary

### Dramatizer (Go)
| Action | File | Lines |
|--------|------|-------|
| CREATE | `internal/cli/gateway.go` | ~220 |
| MODIFY | `internal/cli/root.go` | +2 (add command) |
| MODIFY | `internal/cli/mcp.go` | +35 (HTTP flags + branch) |

### Agent-Forge (TS)
| Action | File | Lines |
|--------|------|-------|
| CREATE | `cli-gateway/server.ts` | ~100 |
| CREATE | `cli-gateway/executor.ts` | ~120 |
| CREATE | `cli-gateway/config.ts` | ~25 |
| CREATE | `cli-gateway/auth.ts` | ~20 |
| CREATE | `cli-gateway/types.ts` | ~30 |
| CREATE | `cli-gateway/package.json` | ~10 |
| CREATE | `cli-gateway/tsconfig.json` | ~10 |

### Backend (TS) — same structure as Agent-Forge
| Action | File | Lines |
|--------|------|-------|
| CREATE | `cli-gateway/*` (7 files) | ~315 total |

### Moonshort Client (TS) — same structure
| Action | File | Lines |
|--------|------|-------|
| CREATE | `cli-gateway/*` (7 files) | ~315 total |

### mobai-agent
| Action | File | Lines |
|--------|------|-------|
| CREATE | `src/server/http.ts` | ~150 |
| CREATE | `src/server/routes.ts` | ~180 |
| CREATE | `src/server/ws-handler.ts` | ~120 |
| CREATE | `src/server/auth.ts` | ~30 |
| MODIFY | `src/server/types.ts` | +40 |
| MODIFY | `src/index.ts` | +30 (server mode) |
| MODIFY | `src/config/schema.ts` | +20 (cli + server schema) |
| CREATE | `src/tool/cli-gateway-client.ts` | ~50 |
| MODIFY | `src/tool/builtin/cli-run.ts` | +30 |
| MODIFY | `src/tool/builtin/discover-cli.ts` | +20 |
| MODIFY | `config.yaml` | +15 |
| CREATE | `web/` (full directory) | ~500 |
