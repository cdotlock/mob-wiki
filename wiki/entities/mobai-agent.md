---
title: mobai-agent
tags: [agent, orchestrator, moonshort, bun, llm, mcp]
sources: [raw/2026-04-14-mobai-agent-memory.md, raw/2026-04-14-orchestrator-skill.md, raw/2026-04-14-mobai-agent-soul.md, raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

Master AI agent orchestrator for the Moonshort content production platform. Drives an end-to-end pipeline that converts novels into screenplays, videos, and playable games through natural language commands. Coordinates [[entities/dramatizer]], [[entities/agent-forge]], [[entities/moonshort-backend]], and [[entities/moonshort-client]] as a unified control plane.

## Architecture

Built on the Bun runtime with the Vercel AI SDK for LLM integration, Effect-ts for structured error handling across all tool executions, and Zod for runtime validation of tool parameters and configuration schemas. Supports Anthropic, OpenAI, and any OpenAI-compatible LLM provider. Default model: Claude Sonnet 4.6 via the ZenMux aggregator endpoint.

### Module Breakdown

**`src/core/runner.ts`** -- The LLM loop engine. Accepts a generate function, a set of tool definitions, and a message history. Drives the agent turn cycle: send messages to the LLM, parse tool calls from the response, execute tools via Effect, append results, and repeat until the LLM produces a final text response or the iteration limit is reached. Handles self-correction when tool calls fail by feeding error messages back into the conversation. Supports retry logic with up to 3 attempts for transient network errors.

**`src/core/loop.ts`** -- The high-level orchestration layer. Manages sessions (create, resume, end), loads skills and memory files, initializes MCP connections, builds the system prompt by combining persona (SOUL.md), memory (MEMORY.md), active skills, and context. Passes everything to the runner for LLM execution. Exposes the tool registry and active skill state to the server layer and TUI.

**`src/core/compaction.ts`** -- Token management with 5 progressive compaction levels. Operates on the message history array, applying increasingly aggressive strategies to fit within the context budget. Works with the Consolidator from the dream system to preserve important context before discarding messages.

**`src/tool/registry.ts`** -- Central tool registry. Stores ToolDefinition objects in a Map, supports filtering by allow/deny lists (ToolProfile), and sorts tools by source priority (builtin > pipeline > mcp). Tools are registered during loop initialization from both builtin definitions and MCP connections.

**`src/tool/mcp-client.ts`** -- MCP connection manager. Handles two transport types: HTTP (StreamableHTTP with SSE fallback) and stdio. For each connected MCP server, fetches the tool list, converts MCP JSON Schema parameters into Zod schemas, and wraps each remote tool as a local ToolDefinition with the naming convention `{serverName}_{toolName}`.

**`src/tool/builtin/`** -- Contains 11 builtin tool files, one per tool. Each exports a factory function that returns a ToolDefinition with Zod-validated parameters and an Effect-based execute function.

**`src/tool/cli-gateway-client.ts`** -- HTTP client for remote CLI gateways. Implements `findGateway()` to match a command name against configured gateways, `execRemoteCli()` to POST commands to gateway `/exec` endpoints, and `listRemoteTools()` to fetch available tools from gateway `/tools` endpoints.

**`src/tool/cli-knowledge.ts`** -- Persistent cache for CLI help documentation. Stores help text, version strings, and usage counts with a 7-day TTL. Used by `cli_help` and `discover_cli` to avoid redundant help fetches.

**`src/tool/ai-adapter.ts`** -- Bridges between the Vercel AI SDK's tool format and the internal ToolDefinition format. Converts Zod-based parameter schemas into the format expected by the `generateText()` function.

**`src/session/`** -- Session persistence layer. Manages session metadata (id, title, timestamps) and message history serialization. Sessions are stored in the SQLite database.

**`src/memory/`** -- Memory file operations. Provides `readMemoryFile()` and `writeMemorySection()` for reading and writing to MEMORY.md, SOUL.md, and USER.md. Also contains the Store interface for SQLite-backed persistence.

**`src/skill/`** -- Skill loading and injection. `loader.ts` reads markdown files with YAML frontmatter from the skills directory, parsing triggers, autoload flags, and priority values. `injector.ts` matches user messages against skill triggers and injects matched skill content into the system prompt.

**`src/dream/`** -- The dream service subsystem. Contains `dream.ts` (DreamService class with timer, trigger, two-phase analysis), `consolidator.ts` (extracts key findings from conversation history), `gitstore.ts` (git-backed persistence for memory files), `prompts.ts` (Phase 1 and Phase 2 prompt templates), and `types.ts`.

**`src/config/`** -- Configuration loading and validation. `schema.ts` defines the full config schema using Zod. `loader.ts` reads config.yaml, applies environment variable overrides, and returns a validated Config object.

**`src/tui/`** -- Terminal UI built with Ink (React for CLI). Renders the interactive chat interface with message display, input handling, and tool execution status indicators.

**`src/server/`** -- HTTP/WebSocket server layer. `http.ts` is the main Bun.serve() entry point, `routes.ts` handles REST API routing, `ws-handler.ts` manages WebSocket connections and message dispatch, `auth.ts` provides Bearer token verification, and `types.ts` defines all request/response/message types.

**`web/`** -- Lightweight web chat client. A Vite + React 19 + TailwindCSS application that connects to the server layer via WebSocket for real-time streaming chat.

## All 11 Builtin Tools

### bash

Raw shell command execution. Spawns a shell process with the given command string.

- **Parameters:** `command` (string, the shell command to execute), `timeout` (number, optional, milliseconds, default 30000), `cwd` (string, optional, working directory)
- **Key behavior:** Executes via `Bun.spawn` with shell expansion enabled. Captures both stdout and stderr. Returns combined output. Process is killed after timeout. Marked as not concurrency-safe (only one bash at a time).

### read_file

Reads a file from disk and returns its content with line numbers.

- **Parameters:** `path` (string, absolute file path), `offset` (number, optional, starting line), `limit` (number, optional, max lines to read)
- **Key behavior:** Returns content in `cat -n` format with line numbers prepended. Supports partial reads via offset and limit for large files.

### write_file

Creates or overwrites a file with the given content.

- **Parameters:** `path` (string, absolute file path), `content` (string, file content to write)
- **Key behavior:** Creates parent directories if they do not exist. Completely replaces existing file content.

### edit_file

Precise line-based text replacement within a file.

- **Parameters:** `path` (string, file path), `old_string` (string, exact text to find), `new_string` (string, replacement text)
- **Key behavior:** Requires an exact match of `old_string` within the file. Fails if the string is not found or matches multiple locations. Designed for surgical edits rather than full rewrites.

### grep

Regex-based content search across files.

- **Parameters:** `pattern` (string, regex pattern), `path` (string, optional, search directory), `include` (string, optional, file glob filter)
- **Key behavior:** Uses ripgrep-style search. Returns matching lines with file paths and line numbers. Supports glob-based file filtering.

### glob

File pattern matching for finding files by name.

- **Parameters:** `pattern` (string, glob pattern like `**/*.ts`), `path` (string, optional, base directory)
- **Key behavior:** Returns matching file paths sorted by modification time. Useful for discovering files before reading them.

### memory_read

Reads one of the three persistent memory files.

- **Parameters:** `file` (string, file name: "MEMORY.md", "SOUL.md", or "USER.md")
- **Key behavior:** Returns the full content of the specified memory file from the `memory/` directory. These files persist across sessions and contain accumulated knowledge.

### memory_write

Writes to a specific section within a memory file.

- **Parameters:** `file` (string, file name), `section` (string, section heading), `content` (string, content to write under that section)
- **Key behavior:** Performs section-level updates within the memory markdown file. After writing, the memory directory is automatically git-committed if `gitAutoCommit` is enabled in config, ensuring a full version history of all memory changes.

### discover_cli

Scans for available CLI tools, both local and remote.

- **Parameters:** `name` (string, optional, specific CLI to check; omit to scan all common CLIs)
- **Key behavior:** When called without a name, probes a hardcoded list of 30+ common CLIs (git, docker, npm, curl, etc.) for availability in PATH. Simultaneously queries all configured remote gateways via `GET /tools` to aggregate their available commands. Returns a combined list organized into `[Remote Gateways]` and `[Local]` sections with version information. Previously discovered CLIs are cached in the CliKnowledgeStore.

### cli_help

Fetches and caches CLI help documentation.

- **Parameters:** `name` (string, CLI tool name), `subcommand` (string, optional, specific subcommand to get help for)
- **Key behavior:** Runs `<name> --help` (or `<name> <subcommand> --help`) and caches the output with a 7-day TTL in the CliKnowledgeStore. Subsequent calls return cached help without re-executing. This enables progressive discovery: the agent calls `discover_cli` to find tools, then `cli_help` to understand them, then `cli_run` to execute them.

### cli_run

Executes a CLI command with smart error recovery and gateway routing.

- **Parameters:** `name` (string, CLI tool name), `args` (string, command arguments), `timeout` (number, optional, milliseconds, default 30000), `cwd` (string, optional, working directory)
- **Key behavior:** First checks if the command matches a configured remote gateway via `findGateway()`. If matched, the command is transparently routed to the remote gateway via HTTP POST to `/exec`. If no gateway matches (or `localFallback` is true and no gateway exists), executes locally via `Bun.spawn`. No shell pipes or redirects are allowed (arguments are parsed and passed directly). On `ENOENT` errors (CLI not found), returns a descriptive error. On non-zero exit codes, returns combined stdout+stderr. Increments usage counters in the CliKnowledgeStore for analytics.

## MCP Integration

### How mcp-client.ts Works

The MCP client supports two transport types:

**HTTP Transport (StreamableHTTP + SSE fallback):** For remote MCP servers like [[entities/agent-forge]]. First attempts to connect via `StreamableHTTPClientTransport` (the newer protocol used by Agent-Forge's `@modelcontextprotocol/sdk`). If that fails (e.g., the server only supports the legacy SSE protocol), falls back to `SSEClientTransport`. This two-phase approach ensures compatibility with both modern and legacy MCP servers.

**Stdio Transport:** For local MCP servers like [[entities/dramatizer]]. Spawns the MCP server binary as a child process (e.g., `/Users/Clock/dramatizer/dram mcp`) and communicates via stdin/stdout pipes using `StdioClientTransport`. Supports custom environment variables and working directory configuration.

### Tool Wrapping Process

After connecting to an MCP server, the client calls `client.listTools()` to fetch all available tools. Each MCP tool is then wrapped as a local `ToolDefinition`:

1. The MCP JSON Schema for the tool's `inputSchema` is converted to a Zod schema via `jsonSchemaToZod()`
2. The tool is registered with the naming convention `{serverName}_{toolName}` (e.g., `dramatizer_list_novels`, `agent-forge_skills__list`)
3. The execute function wraps `client.callTool()` in an Effect, extracting text content from the MCP result array
4. All wrapped tools are marked with `source: "mcp"` and `concurrencySafe: true`

### Connected MCP Servers

| Server | Transport | URL/Command | Tool Count |
|--------|-----------|-------------|------------|
| [[entities/agent-forge]] | HTTP StreamableHTTP | `http://localhost:8001/mcp` | 48 tools |
| [[entities/dramatizer]] | stdio | `/Users/Clock/dramatizer/dram mcp` | 14 tools |

## Server Layer

The server layer (`src/server/`) provides remote access to the agent via HTTP REST API and WebSocket. Built on Bun's native `Bun.serve()` with integrated WebSocket support. Activated with `--server --port 3100`.

### REST API Endpoints

All endpoints are prefixed with `/api/` and require `Authorization: Bearer <key>` authentication.

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `GET` | `/api/health` | Health check with connected MCP status | None | `{ ok: true, data: { status: "ok", uptime: number, tools: number, skills: string[] } }` |
| `GET` | `/api/sessions` | List all sessions for the current user | None | `{ ok: true, data: SessionInfo[] }` |
| `POST` | `/api/sessions` | Create a new chat session | `{ title?: string }` | `{ ok: true, data: { sessionId: string } }` |
| `GET` | `/api/sessions/:id` | Get session details including message history | None | `{ ok: true, data: SessionInfo }` |
| `DELETE` | `/api/sessions/:id` | End and close a session | None | `{ ok: true, data: null }` |
| `POST` | `/api/sessions/:id/message` | Send a message (non-streaming, returns full response) | `{ content: string }` | `{ ok: true, data: { response: string } }` |
| `GET` | `/api/skills` | List all skills with activation status | None | `{ ok: true, data: SkillInfo[] }` |
| `POST` | `/api/skills/:name/activate` | Activate a skill by name | None | `{ ok: true, data: null }` |
| `GET` | `/api/memory/:type` | Read a memory file (MEMORY, SOUL, or USER) | None | `{ ok: true, data: { content: string } }` |

All responses follow the envelope format `{ ok: boolean, data?: T, error?: string }`.

### WebSocket Protocol

The WebSocket endpoint is at `/ws`. Bidirectional JSON messages enable real-time streaming chat.

**Client-to-Server Messages:**

```json
{ "type": "create_session", "title": "optional session title" }
```
Creates a new chat session. Server responds with `session_created`.

```json
{ "type": "message", "sessionId": "session-id", "content": "user message text" }
```
Sends a chat message. Server streams back `text`, `tool_progress`, `thinking`, and `done` messages.

```json
{ "type": "end_session", "sessionId": "session-id" }
```
Ends a session. Server responds with `session_ended`.

**Server-to-Client Messages:**

```json
{ "type": "session_created", "sessionId": "session-id" }
```
Confirms session creation with the assigned session ID.

```json
{ "type": "text", "content": "incremental assistant text chunk" }
```
Streaming text from the assistant response. Multiple `text` messages are concatenated by the client.

```json
{ "type": "tool_progress", "toolName": "cli_run", "status": "running" | "done" | "error", "result": "optional result text" }
```
Reports tool execution progress. Status transitions: `running` -> `done` or `running` -> `error`.

```json
{ "type": "thinking", "content": "reasoning text" }
```
Thinking/reasoning content from the LLM (when supported by the model).

```json
{ "type": "done", "usage": { "promptTokens": 1234, "completionTokens": 567 } }
```
Signals the complete end of an assistant response with token usage statistics.

```json
{ "type": "error", "message": "error description" }
```
Reports an error condition.

```json
{ "type": "session_ended", "sessionId": "session-id" }
```
Confirms session termination.

### Static File Serving

Non-API paths (`GET /` and all paths not starting with `/api/`) serve static files from `web/dist/`. This allows the web client to be hosted from the same server on the same port, requiring no separate static file server or reverse proxy. MIME types are mapped for HTML, JS, CSS, JSON, PNG, SVG, ICO, WOFF2, WOFF, and source maps.

### Server Mode Activation

```bash
bun run dev -- --server              # Server mode on default port 3100
bun run dev -- --server --port 8080  # Custom port
```

When `config.server.enabled = true` or `--server` flag is passed, the HTTP server starts instead of the TUI. The server creates the same `AgentLoop` instance as TUI mode and forwards WebSocket messages to `loop.handleMessage()`.

## Web Client

### Tech Stack

Vite 6 + React 19 + TailwindCSS + react-markdown. Zero backend dependencies beyond the WebSocket connection to the agent server.

### Components

- **`App.tsx`** -- Main layout component. Manages sessions state, message state, WebSocket connection, and tool execution indicators. Renders a sidebar (SessionList) and main chat area (ChatView + InputBar + ToolStatus).
- **`ChatView.tsx`** -- Message list with markdown rendering via react-markdown. Displays user messages, assistant responses, and tool execution results in a scrollable container.
- **`InputBar.tsx`** -- Text input with send button. Handles Enter key submission and disabled state during loading.
- **`MessageBubble.tsx`** -- Renders a single message (user, assistant, or tool result) with appropriate styling and markdown formatting.
- **`SessionList.tsx`** -- Sidebar session selector. Shows all sessions with selection highlighting and new-session creation.
- **`ToolStatus.tsx`** -- Active tool execution indicators. Shows which tools are currently running with status badges.

### useWebSocket Hook

Located at `hooks/useWebSocket.ts`. Manages the WebSocket connection lifecycle with auto-reconnect on disconnection. Exposes `state` (connecting/connected/disconnected), `lastMessage` (most recent parsed server message), and `send()` (function to send client messages). The App component reacts to `lastMessage` changes to update the UI.

### Build and Dev Instructions

```bash
cd web && npm install && npm run build   # Production build -> web/dist/
cd web && npm run dev                    # Development mode with Vite dev server + API proxy
```

The production build output in `web/dist/` is automatically served by the agent server at `GET /`.

## Execution Modes

**Interactive TUI (default):** `bun run dev` -- Launches the Ink-based terminal UI with full interactive chat. Supports multi-line input, tool execution display, and session management.

**Single query (--run):** `bun run dev -- --run "your question here"` -- Runs a single query, prints the response, and exits. Useful for scripting and automation.

**Pipe input:** `echo "query" | bun run dev` -- Reads from stdin, processes the query, and exits. Enables integration with shell pipelines.

**Server mode (--server):** `bun run dev -- --server --port 3100` -- Starts the HTTP/WebSocket server instead of the TUI. Enables remote access via REST API, WebSocket, and the web client.

**Session resume (--session):** `bun run dev -- --session=<id>` -- Resumes a previous session by loading its message history from the database.

**Compiled binary mode:** The project can be compiled to a standalone binary via `bun build`, producing a single executable that includes all dependencies.

## Memory System

Three persistent markdown files stored in `memory/` (git-tracked):

### MEMORY.md

Stores factual knowledge the agent has learned about the platform. Includes platform locations (file paths for each project), MCP connection counts, CLI tool names and paths, database connection details, and operational notes. Updated by the agent via `memory_write` when it discovers new facts or corrects existing ones.

### SOUL.md

Agent persona and behavioral configuration. Defines language preference (Chinese by default, English when the user uses English), communication style (concise, direct), and tool usage strategy (which platform tools to prefer for different operations). This file shapes the system prompt personality.

### USER.md

User profiles and preferences. Stores information about individual users that the agent has learned across sessions.

### Dream Service

The dream service is an autonomous background process that periodically analyzes conversation history and updates memory files.

**Configuration:** Controlled by the `dream` section in config.yaml. Key settings: `enabled` (boolean), `intervalHours` (default 4), `triggerOnSessionEnd` (boolean), `model` (default claude-haiku-4.5), `confidenceThreshold` (0.8), `removeThreshold` (0.9), `maxIterations` (10), `gitAutoCommit` (true).

**Timer:** The DreamService starts an interval timer at `intervalHours * 60 * 60 * 1000` milliseconds. Each tick triggers the `trigger()` method.

**Phase 1 -- Extraction:** The Consolidator reads unprocessed conversation history from `history.jsonl` (tracked by a cursor in `.dream_cursor`). It uses an LLM call with `DREAM_PHASE1_PROMPT` to extract key findings, patterns, and corrections from recent conversations.

**Phase 2 -- Integration:** Uses `DREAM_PHASE2_PROMPT` with the extracted findings to generate specific updates to MEMORY.md, SOUL.md, and USER.md. Updates are applied with confidence scoring -- only findings above `confidenceThreshold` (0.8) are written. Findings above `removeThreshold` (0.9) can trigger removal of outdated information.

**Git-backed persistence:** The GitStore class manages git operations on the memory directory. After each dream cycle, changes are automatically committed with descriptive messages. This provides a full audit trail and rollback capability for all memory mutations.

**TUI commands:** `/dream` (trigger a dream cycle manually), `/dream-log` (view dream history from `dream-log.jsonl`), `/dream-restore` (restore memory files from a previous git commit), `/dream-status` (show current dream cursor position and last run time).

## Skill System

Skills are markdown files with YAML frontmatter stored in the `skills/` directory. They inject domain-specific knowledge into the system prompt when triggered.

### Skill Frontmatter Schema

```yaml
---
name: skill-name
description: Human-readable description
triggers: ["keyword1", "keyword2"]
autoload: true/false
priority: 10
---
```

- **name:** Identifier for the skill (defaults to filename without extension)
- **description:** Brief description of what the skill provides
- **triggers:** Array of keywords that activate this skill when matched in user messages
- **autoload:** If true, the skill is always loaded into the system prompt regardless of triggers
- **priority:** Numeric priority for ordering (higher = loaded first). Used when multiple skills are active.

### Available Skills (6 total)

| Skill | Directory | Autoload | Priority | Triggers |
|-------|-----------|----------|----------|----------|
| `orchestrator` | `general/` | yes | 20 | orchestrate, pipeline, e2e |
| `coding` | `general/` | no | 0 | (general coding tasks) |
| `debugging` | `general/` | no | 0 | (debugging tasks) |
| `agent-forge-video` | `agent-forge/` | no | 10 | agent-forge, video, episode, forge |
| `dramatizer-pipeline` | `dramatizer/` | no | 10 | dramatizer, pipeline, screenplay, dram |
| `moonshort-game-client` | `moonshort/` | no | 10 | moonshort, cocos, client, phase, AppCore |

### Trigger Matching and System Prompt Injection

When a user message arrives, the skill injector scans all loaded skills' trigger arrays. If any trigger keyword appears in the user message (case-insensitive), that skill's markdown content is appended to the system prompt for the current LLM call. Autoloaded skills are always present in the system prompt. Skills are sorted by priority (descending) before injection, ensuring higher-priority skills appear first in the context.

## Token Management (Compaction)

The compaction system ensures the message history fits within the LLM's context window. It applies 5 progressively aggressive levels, stopping as soon as the history fits within budget.

### Context Budget Calculation

```
Budget = contextWindow - maxOutput - reservedBuffer
       = 200,000 - 8,192 - 20,000
       = 171,808 tokens available for message history
```

### Level 1: Orphan Cleanup

Removes tool result messages that have no corresponding tool call in the assistant messages. This happens when earlier messages have been removed by previous compaction cycles, leaving dangling tool results. Also removes assistant tool-call messages whose results are missing.

### Level 2: Micro-Compact (Stub Old Tool Results)

Replaces the content of old tool result messages with a short stub like `[result truncated]`, keeping only the most recent N tool results intact (configured by `microcompactKeep`, default 8). This preserves the conversation structure while reducing token count from large tool outputs.

### Level 3: Truncate Large Results

For individual tool results exceeding `maxToolResultChars` (default 16,384 characters), truncates them to show only the first and last portions with a `[... truncated ...]` marker in the middle. This handles cases where a single tool output (e.g., a large file read) dominates the context.

### Level 4: Delete Oldest Turns (with Consolidator)

Removes the oldest non-system message turns from the history. Before deletion, if a Consolidator is available (from the dream service), it is called to extract and preserve key findings from the about-to-be-deleted messages. The `keepRecentTurns` parameter (default 4) protects the most recent turns from removal. Certain tools are marked as non-compactable (`memory_read`, `memory_write`, `pipeline_run`, `pipeline_status`) and their results are preserved.

### Level 5: Emergency Truncation

Last resort. Drops the oldest non-system messages one by one until the budget is met. No consolidation is performed. This only activates when all other levels have been applied and the history still exceeds the budget.

## CLI Gateway Routing

### Configuration

The `cli.gateways` section in `config.yaml` maps gateway names to remote CLI gateway servers:

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

Each gateway entry specifies: `url` (gateway base URL), `apiKey` (Bearer token, supports `${ENV_VAR}` interpolation), `tools` (array of command names this gateway handles), and `timeout` (milliseconds, default 30000).

### findGateway() Routing Logic

Located in `src/tool/cli-gateway-client.ts`. When `cli_run` receives a command:

1. Iterates through all configured gateways
2. Checks if the command name appears in the gateway's `tools` array
3. Returns the first matching gateway configuration
4. If no gateway matches, returns null (command executes locally)

### discover_cli Remote Tool Aggregation

When `discover_cli` is called without a specific name, it queries all configured gateways in parallel via `GET /tools`. The results are merged with locally-discovered CLIs and presented in two sections: `[Remote Gateways]` listing tools with their gateway name, and `[Local]` listing tools found in PATH.

### Transparency

The entire gateway routing mechanism is invisible to the LLM agent. From the agent's perspective, it uses `discover_cli` to find tools, `cli_help` to learn about them, and `cli_run` to execute them. Whether execution happens locally or remotely is an implementation detail handled by the routing layer.

## Configuration

### Full config.yaml Structure

```yaml
agent:
  defaultModel: "anthropic/claude-sonnet-4.6"   # LLM model identifier
  provider: "openai-compatible"                   # "openai-compatible", "openai", "anthropic"
  baseUrl: "https://zenmux.ai/api/v1"            # API endpoint (for openai-compatible)
  # apiKey: set via LLM_API_KEY env var
  maxOutputTokens: 8192                           # Max tokens per LLM response
  contextWindow: 200000                           # Total context window size
  reservedBuffer: 20000                           # Tokens reserved for system prompt + tools
  maxIterations: 80                               # Max tool-call loop iterations per request

compaction:
  microcompactKeep: 8          # Number of recent tool results to keep intact in L2
  maxToolResultChars: 16384    # Max chars per tool result before L3 truncation
  autoCompactEnabled: true     # Enable automatic compaction before each LLM call
  keepRecentTurns: 4           # Turns protected from L4 removal
  consolidatorModel: null      # Optional separate model for consolidation

memory:
  dreamIntervalHours: 4        # Legacy; use dream.intervalHours instead
  dreamModel: "claude-haiku"   # Legacy; use dream.model instead
  gitAutoCommit: true          # Auto git commit on memory_write

skills:
  directory: "./skills"        # Path to skills directory

database:
  path: "./data/mobai.db"      # SQLite database file path
  walMode: true                # Enable WAL mode for concurrent reads

server:
  enabled: false               # Start in server mode by default
  port: 3100                   # HTTP/WS server port

dream:
  enabled: false               # Enable the dream service
  intervalHours: 4             # Hours between automatic dream cycles
  triggerOnSessionEnd: true    # Run dream when a session ends
  model: "anthropic/claude-haiku-4.5"  # Model for dream analysis
  confidenceThreshold: 0.8    # Minimum confidence to write a finding
  removeThreshold: 0.9        # Minimum confidence to remove outdated info
  maxIterations: 10            # Max LLM iterations per dream cycle
  gitAutoCommit: true          # Git commit after dream updates

cli:
  gateways: {}                 # Remote CLI gateway configurations
  localFallback: true          # Fall back to local execution if no gateway matches

mcp:
  servers:
    agent-forge:
      url: "http://localhost:8001/mcp"
      transport: "http"
    dramatizer:
      command: "/Users/Clock/dramatizer/dram"
      args: ["mcp"]
      transport: "stdio"
```

### Environment Variable Overrides

| Variable | Purpose |
|----------|---------|
| `LLM_API_KEY` | API key for the LLM provider |
| `LLM_BASE_URL` | Override the LLM API endpoint |
| `MOBAI_API_KEY` | API key for the server layer authentication |
| `OPENAI_API_KEY` | OpenAI API key (used when provider is "openai") |
| `DRAMATIZER_CLI_KEY` | Bearer token for Dramatizer CLI gateway |
| `BACKEND_CLI_KEY` | Bearer token for Backend CLI gateway |
| `CLIENT_CLI_KEY` | Bearer token for Moonshort Client CLI gateway |

## Testing

23 test files across the codebase, organized by module:

### Unit Tests

- `tests/core/runner.test.ts` -- Runner loop mechanics, tool call parsing, self-correction
- `tests/core/compaction.test.ts` -- All 5 compaction levels, budget calculation, edge cases
- `tests/core/loop.test.ts` -- AgentLoop session management, skill loading, MCP initialization
- `tests/tool/registry.test.ts` -- Tool registration, filtering, source ordering
- `tests/tool/cli-knowledge.test.ts` -- Help caching, TTL expiry, usage counting
- `tests/tool/builtin/bash.test.ts` -- Shell execution, timeout, error handling
- `tests/tool/builtin/file-ops.test.ts` -- read_file, write_file, edit_file operations
- `tests/tool/builtin/search.test.ts` -- grep and glob tool behavior
- `tests/tool/builtin/cli-tools.test.ts` -- discover_cli, cli_help, cli_run
- `tests/skill/loader.test.ts` -- Skill file parsing, frontmatter extraction, directory loading
- `tests/config/loader.test.ts` -- Config loading, validation, environment variable overrides
- `tests/memory/store.test.ts` -- SQLite store CRUD operations
- `tests/memory/markdown.test.ts` -- Memory file read/write, section parsing
- `tests/session/manager.test.ts` -- Session creation, resume, persistence
- `tests/session/message.test.ts` -- Message serialization, token estimation

### E2E Tests

- `tests/e2e/integration.test.ts` -- Full agent integration with mock LLM
- `tests/e2e/full-validation.test.ts` -- End-to-end validation with real tool execution
- `tests/e2e/cli-mode.test.ts` -- --run mode, pipe mode, session resume

### MCP Tests

- `tests/tool/mcp-client.test.ts` -- MCP connection, tool wrapping, transport fallback

### Dream Tests

- `tests/dream/consolidator.test.ts` -- Finding extraction from conversation history
- `tests/dream/gitstore.test.ts` -- Git operations, commit, restore
- `tests/dream/dream.test.ts` -- DreamService lifecycle, Phase 1/2 analysis, timer

### Benchmark

- `tests/benchmark/token-profile.test.ts` -- Token estimation accuracy, compaction performance

## Related

- [[entities/dramatizer]] -- Novel-to-screenplay pipeline (MCP stdio connection)
- [[entities/agent-forge]] -- Screenplay-to-video platform (MCP HTTP connection)
- [[entities/moonshort-backend]] -- Game engine and admin dashboard (CLI gateway)
- [[entities/moonshort-client]] -- Cocos game frontend (CLI gateway)
- [[entities/cli-gateway]] -- Remote CLI execution protocol
- [[concepts/four-layer-philosophy]] -- SKILL/CLI/MCP/API design framework
- [[concepts/cli-gateway-protocol]] -- HTTP API specification for CLI gateways

## Sources

- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
- [Orchestrator skill](../raw/2026-04-14-orchestrator-skill.md)
- [Agent soul](../raw/2026-04-14-mobai-agent-soul.md)
- [CLI Gateway design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
