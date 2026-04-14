---
title: Agent-Forge
tags: [nextjs, mcp, video, agent, llm, prisma, react]
sources: [raw/2026-04-14-agent-forge-skill.md, raw/2026-04-14-mobai-agent-memory.md, raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

Next.js application that converts interactive screenplays into video episodes using AI agents. Exposes 48 MCP tools via HTTP StreamableHTTP, a full REST API with 43 endpoint files, and an internal agent chat loop. Serves as the video production brain of the Moonshort platform, taking story trees from [[entities/dramatizer]] and producing video assets.

## Tech Stack

- **Framework:** Next.js 16.1.6 (App Router)
- **UI Library:** React 19.2.3
- **Component Library:** Ant Design 6.3.0
- **Styling:** TailwindCSS 4
- **Database:** PostgreSQL via Prisma ORM v6.6.0
- **MCP SDK:** @modelcontextprotocol/sdk (WebStandardStreamableHTTPServerTransport)
- **LLM:** OpenAI-compatible (configurable model and endpoint)
- **Storage:** Alibaba Cloud OSS (images, videos, audio)
- **Observability:** Langfuse (LLM call tracing and evaluation)
- **Repository:** github.com/Rydia-China/Agent-Forge
- **Location:** `/Users/Clock/video-loop/Agent-Forge/`
- **Port:** 8001

## MCP Architecture

### Registry Singleton

The MCP system is built on a Registry singleton pattern. On application startup, the Registry initializes all configured providers. Each provider implements the `McpProvider` interface, which defines `listTools()` and `callTool()` methods. When an MCP request arrives, the Registry routes it to the appropriate provider based on the tool name.

### Tool Naming Convention

Tool names follow the pattern `qualifyToolName(provider, tool)` which produces `providerName__toolName` (double underscore separator). For example, a tool named `list` in the `skills` provider becomes `skills__list`. From [[entities/mobai-agent]]'s perspective, these appear as `agent-forge_skills__list` (the MCP server name is prepended by the agent's MCP client).

### MCP Endpoints

- **`/mcp`** -- Exposes all 48 tools from all providers through a single `WebStandardStreamableHTTPServerTransport` endpoint. This is the primary endpoint used by [[entities/mobai-agent]].
- **`/mcp/[provider]`** -- Scoped endpoint that exposes only the tools from a specific provider. Useful for focused integrations that only need a subset of capabilities.

### Core Providers (Always Active)

**`skills`** -- Manages Agent-Forge skills (reusable prompt templates with versioning). Tools: `skills__list`, `skills__get`, `skills__create`, `skills__update`, `skills__delete`, `skills__get_version`, `skills__promote`. Required env vars: none.

**`mcp_manager`** -- Meta-provider that manages dynamic MCP providers. Tools: `mcp_manager__list` (list all providers), `mcp_manager__create` (create a new dynamic MCP from JavaScript code), `mcp_manager__reload` (reload a provider), `mcp_manager__use` (invoke a tool from a specific provider by name -- this is the gateway for calling tools on dynamic MCP providers). Required env vars: none.

**`ui`** -- UI interaction tools for the Agent-Forge web dashboard. Tools for managing the web UI state, sending notifications, and controlling display elements. Required env vars: none.

**`memory`** -- Persistent memory system for the internal agent. Stores facts, context, and learned information across sessions. Required env vars: none.

**`sync`** -- Synchronization tools for coordinating data between Agent-Forge and upstream systems. Handles novel/episode data sync. Required env vars: depends on sync targets.

### Catalog Providers (Lazy-Loaded)

**`biz_db`** -- Direct business database access. Provides SQL query tools for reading and writing to the PostgreSQL database. Required env vars: `DATABASE_URL`.

**`apis`** -- External API integration tools. Wraps third-party APIs (image generation, text-to-speech, translation) as MCP tools. Required env vars: varies per API (API keys for each service).

**`video_mgr`** -- Video management and generation tools. Core production provider that handles novel listing, episode creation, content management, resource tracking, and generation status. Required env vars: `DATABASE_URL`, `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`.

**`langfuse`** -- Langfuse observability integration. Provides tools for querying LLM traces, evaluating outputs, and managing datasets. Required env vars: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.

**`langfuse_admin`** -- Langfuse administrative tools. Manages Langfuse projects, users, and configuration. Required env vars: same as `langfuse`.

**`subagent`** -- Sub-agent spawning and management. Allows the main agent to create and coordinate child agents for parallel task execution. Required env vars: LLM API configuration.

**`oss`** -- Alibaba Cloud OSS file operations. Upload, download, list, and delete files in cloud storage. Required env vars: `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`, `OSS_BUCKET`, `OSS_REGION`.

## Dynamic MCP Sandbox

Agent-Forge supports creating custom MCP providers at runtime through a JavaScript sandbox powered by QuickJS (via quickjs-emscripten). This enables users to define new tools without restarting the server.

### Code Format Requirements

Sandbox code **must** use CommonJS `module.exports` format. ES modules (`export default`, `export function`) are not supported.

```javascript
// Correct format
module.exports.tools = [
  {
    name: "my_tool",
    description: "Tool description",
    inputSchema: { type: "object", properties: { param1: { type: "string" } } }
  }
];

module.exports.callTool = async function(name, args) {
  if (name === "my_tool") {
    return { content: [{ type: "text", text: "result" }] };
  }
  throw new Error("Unknown tool: " + name);
};
```

### Built-in Globals

The sandbox provides these global objects and functions:

- **`console.log/warn/error`** -- Output is forwarded to the host process with a `[sandbox:name]` prefix for identification.
- **`fetch(url, options)`** -- Asynchronous HTTP client. Returns a standard Response-like object.
- **`fetchSync(url, options)`** -- Synchronous HTTP client. Returns `{ status, body, ok, json(), text() }`. Useful when async patterns are problematic in the sandbox.
- **`getSkill(name)`** -- Reads an Agent-Forge skill by name. Returns the skill's content string.
- **`callToolSync(name, args)`** -- Synchronously invokes another registered MCP tool. The tool name should be the bare tool name without the provider prefix (e.g., `"tool_name"` not `"provider__tool_name"`). Returns `{ content: [{ type: "text", text: "..." }] }`.

### Limitations

- **No `JSON` global.** The QuickJS sandbox does not provide the `JSON` object. Use string concatenation for JSON construction, or use `fetchSync(...).json()` for parsing responses.
- **callTool return format must be MCP CallToolResult:** `{ content: [{ type: "text", text: "..." }] }`. Other return formats cause `callTool failed in sandbox` errors.
- **Invocation from mobai-agent:** Dynamic MCP tools are called via the `mcp_manager__use` tool with parameters `{ provider: "my-mcp", tool: "tool_name", args: {...} }`. The tool name does not include the provider prefix.

## Agent Loop

Agent-Forge contains its own internal agent loop (separate from [[entities/mobai-agent]]):

1. **Load session** -- Retrieve or create a ChatSession with message history
2. **Build system prompt** -- Combine base persona, active skills, and context (key resources, recent tool results)
3. **LLM call** -- Send messages to the configured LLM with all available MCP tools
4. **Tool execution** -- Execute any tool calls returned by the LLM via the MCP Registry
5. **Persist messages** -- Save all messages (user, assistant, tool results) to the database
6. **Extract key resources** -- Identify and store important outputs (images, videos, data) as KeyResource records for future reference

This loop is used by both the `/api/chat` endpoint and the `/api/tasks` system.

## REST API Routes (43 Endpoint Files)

### Chat and Tasks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a message to the agent (synchronous response) |
| `POST` | `/api/tasks` | Submit an async task with a message |
| `GET` | `/api/tasks/:id` | Query task status |
| `GET` | `/api/tasks/:id/events` | SSE stream of task progress events |
| `POST` | `/api/tasks/:id/cancel` | Cancel a running task |

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sessions` | List all chat sessions |
| `GET` | `/api/sessions/:id` | Get session details with messages |
| `POST` | `/api/sessions` | Create a new session |
| `DELETE` | `/api/sessions/:id` | Delete a session |

### Skills

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/skills` | List all skills |
| `GET` | `/api/skills/:id` | Get a specific skill |
| `POST` | `/api/skills` | Create a new skill |
| `PUT` | `/api/skills/:id` | Update a skill |
| `DELETE` | `/api/skills/:id` | Delete a skill |
| `GET` | `/api/skills/:id/versions` | List skill versions |
| `GET` | `/api/skills/:id/versions/:versionId` | Get a specific version |
| `POST` | `/api/skills/:id/production` | Promote a version to production |

### MCP Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/mcps` | List all MCP providers |
| `POST` | `/api/mcps` | Create a dynamic MCP provider |
| `PUT` | `/api/mcps/:id` | Update a dynamic MCP provider |
| `DELETE` | `/api/mcps/:id` | Delete a dynamic MCP provider |
| `POST` | `/api/mcps/:id/reload` | Reload a provider |

### API Integrations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/apis` | List configured API integrations |
| `POST` | `/api/apis` | Add a new API integration |
| `PUT` | `/api/apis/:id` | Update an API integration |
| `DELETE` | `/api/apis/:id` | Remove an API integration |

### Video Production

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/video/novels` | List available novels |
| `GET` | `/api/video/novels/:id` | Get novel details |
| `GET` | `/api/video/novels/:id/episodes` | List episodes for a novel |
| `POST` | `/api/video/episodes` | Create a new episode |
| `PUT` | `/api/video/episodes/:id` | Update an episode |
| `GET` | `/api/video/episodes/:id/content` | Get episode content (screenplay JSON) |
| `GET` | `/api/video/episodes/:id/resources` | List attached resources (images, audio, video) |
| `GET` | `/api/video/episodes/:id/status` | Check generation status |

### Key Resources

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/key-resources` | List key resources |
| `GET` | `/api/key-resources/:id` | Get a specific key resource |
| `GET` | `/api/key-resources/:id/versions` | List resource versions |

### Synchronization

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sync` | Trigger data synchronization with upstream |

### File Upload

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/oss/upload` | Upload a file to Alibaba Cloud OSS |

### Public Assets

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/public/*` | Serve public assets (images, videos) |

## Data Model

### Skill / SkillVersion

Skills are reusable prompt templates. Each Skill has multiple SkillVersions, with one marked as "production". Versions enable rollback and A/B testing of different prompt strategies. Fields: id, name, description, content, version, isProduction, createdAt, updatedAt.

### ChatSession / ChatMessage

Chat sessions track multi-turn conversations with the agent. Each ChatSession contains an ordered list of ChatMessages with roles (user, assistant, tool). Sessions are identified by a unique session_id and include metadata (title, createdAt, lastActiveAt). Messages store the full content including tool call details and results.

### User

User accounts with authentication credentials. Fields: id, email, name, role (user/admin), createdAt.

### Task

Asynchronous task tracking. Tasks have a lifecycle: pending -> running -> completed/failed/cancelled. Each task references a session and stores the result. Tasks emit SSE events for real-time progress monitoring.

### KeyResource / KeyResourceVersion

Important outputs extracted from agent conversations. KeyResources are identified by type (image, video, data, text) and tagged with metadata for searchability. KeyResourceVersions track changes over time, enabling comparison and rollback.

### ImageGeneration

Tracks AI image generation requests. Stores the prompt, model, parameters, result URL, and generation time. Linked to episodes and key resources.

## CLI: forge-eval

Evaluation harness located at `cli/` in the Agent-Forge repository. Used for automated testing and quality evaluation of video production workflows.

### Commands

| Command | Description |
|---------|-------------|
| `forge-eval run` | Submit an evaluation task to Agent-Forge at localhost:8001. Sends a task via `POST /api/video/tasks` and polls SSE events until completion. |
| `forge-eval report` | Generate a quality report from completed evaluation runs. Aggregates scores and identifies regressions. |
| `forge-eval promote` | Promote a successful evaluation configuration to production. |
| `forge-eval diff` | Compare two evaluation runs side-by-side. |
| `forge-eval compare` | Compare multiple evaluation runs across different parameters. |
| `forge-eval trend` | Show quality trends over time from historical evaluation data. |

### Connection

forge-eval connects to the Agent-Forge REST API at `http://localhost:8001`. It submits evaluation tasks, polls for completion via SSE at `/api/tasks/:id/events`, and collects results for reporting.

## Deployment

- **Docker:** Containerized deployment with Docker. Port 8001 exposed.
- **Production:** SSH access at `47.97.112.115`. Production database is PostgreSQL (same Docker instance, database name: `agent_forge`).
- **Environment:** Requires `DATABASE_URL`, LLM API keys, OSS credentials, and optionally Langfuse credentials.

## Related

- [[entities/mobai-agent]] -- Orchestrator agent that connects to Agent-Forge via MCP HTTP
- [[entities/dramatizer]] -- Upstream pipeline that produces story trees for video production
- [[entities/cli-gateway]] -- CLI gateway for remote forge-eval execution
- [[concepts/cli-gateway-protocol]] -- HTTP API specification for the CLI gateway

## Sources

- [Agent-Forge skill](../raw/2026-04-14-agent-forge-skill.md)
- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
- [CLI Gateway design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
