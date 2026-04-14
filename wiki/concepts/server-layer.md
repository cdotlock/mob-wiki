---
title: "mobai-agent Server Layer"
tags: [http, websocket, api, web-client, server, react]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

# mobai-agent Server Layer

## Purpose and Architecture

The server layer enables remote access to [[entities/mobai-agent]] from web clients and external systems. Without the server layer, mobai-agent is accessible only through its terminal-based TUI, which requires a direct SSH or physical terminal connection to the machine running the agent. This limits usage to a single operator sitting at the console.

The server layer replaces this terminal-only interface with a network-accessible HTTP/WebSocket server that exposes the same capabilities through REST API endpoints and real-time WebSocket communication. The same `AgentLoop` core that drives the TUI mode drives the server mode. The server is not a separate application or a wrapper around the agent -- it is a different InputPort attached to the same loop. Messages arrive over HTTP or WebSocket instead of through terminal stdin, and responses are sent over HTTP or WebSocket instead of through terminal stdout, but the agent's reasoning, tool execution, memory system, and skill activation are identical in both modes.

This architectural choice -- same core, different transport -- means that every capability available in TUI mode is automatically available in server mode, and behavior is guaranteed to be consistent across both. There is no "server-only" or "TUI-only" functionality.

## Activation

The server layer is controlled through both CLI flags and configuration:

### CLI Flag Activation

```bash
bun run dev -- --server               # Start in server mode on default port (3100)
bun run dev -- --server --port 3100   # Start in server mode on specified port
```

### Configuration File Activation

In `config.yaml`:

```yaml
server:
  enabled: true
  port: 3100
```

When `config.server.enabled` is `true` in the configuration or the `--server` CLI flag is present, `src/index.ts` starts the HTTP server instead of the TUI. Currently, server mode and TUI mode are mutually exclusive -- the process runs in one mode or the other, not both simultaneously. Future versions may support running both concurrently (server for remote access, TUI for local debugging).

The default port is 3100. This port was chosen to avoid conflicts with common development servers (3000 for React/Next.js, 5173 for Vite, 8000/8001 for backend services, 9001-9003 for CLI gateways).

## REST API

All REST endpoints are prefixed with `/api/`. Authentication is required for all `/api/` endpoints. Responses follow a consistent envelope format.

### Authentication

Authentication uses Bearer token authentication via the `MOBAI_API_KEY` environment variable:

```
Authorization: Bearer <MOBAI_API_KEY>
```

The authentication logic is implemented in `src/server/auth.ts`. If `MOBAI_API_KEY` is not set or is empty, the server operates in open mode where all requests are accepted without authentication. Open mode is intended for local development only. In production deployments, `MOBAI_API_KEY` must be set to a strong, random token.

When authentication fails, the server returns:

```json
{ "ok": false, "error": "Unauthorized" }
```

with HTTP status 401.

### CORS Configuration

The server sets `Access-Control-Allow-Origin: *` on all API responses, allowing the web client to be served from any origin. CORS preflight (`OPTIONS`) requests are handled by returning 200 with the following headers:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

### Response Envelope Format

All API responses use the following TypeScript type:

```typescript
interface ApiResponse<T> {
  ok: boolean;
  // true if the request was processed successfully, false otherwise.

  data?: T;
  // The response payload. Present when ok is true.
  // Type varies by endpoint (see individual endpoint documentation below).

  error?: string;
  // Error description. Present when ok is false.
  // Human-readable string describing what went wrong.
}
```

### Endpoint: GET /api/health

Returns the server's status and basic operational metrics.

**Response body (`data` field):**

```typescript
{
  status: "ok";
  // Always "ok" if the server is running and responsive.

  uptime: number;
  // Server process uptime in seconds (Math.floor(process.uptime())).

  tools: number;
  // Total number of tools registered in the agent's tool registry.
  // Includes built-in tools, MCP tools from all connected servers,
  // and any dynamically registered tools.

  skills: string[];
  // Names of currently active skills. Example: ["dramatizer/pipeline",
  // "general/orchestrator"].
}
```

### Endpoint: POST /api/sessions

Creates a new agent session.

**Request body:**

```json
{
  "title": "Optional session title"
}
```

The `title` field is optional. If omitted, the session is created with a default title ("Untitled").

**Response body (`data` field):**

```typescript
{
  sessionId: string;
  // UUID of the newly created session.
}
```

**HTTP status:** 201 (Created).

### Endpoint: GET /api/sessions

Lists all sessions for the current user.

**Response body (`data` field):**

```typescript
Array<{
  id: string;
  // UUID of the session.

  title: string;
  // Session title. "Untitled" if no title was provided at creation.

  createdAt: string;
  // ISO 8601 timestamp of session creation.

  messageCount: number;
  // Number of messages in the session.
}>
```

### Endpoint: GET /api/sessions/:id

Returns details of a specific session including its full message history.

**Response body (`data` field):**

```typescript
{
  id: string;
  // UUID of the session.

  title: string;
  // Session title.

  createdAt: string;
  // ISO 8601 timestamp of session creation.

  messages: Array<{
    role: "user" | "assistant" | "tool";
    // Message role.

    content: string;
    // Message text content.

    createdAt: string;
    // ISO 8601 timestamp of when the message was stored.
  }>;
}
```

**Error:** Returns 404 with `{ ok: false, error: "Session not found" }` if the session ID does not exist.

### Endpoint: DELETE /api/sessions/:id

Ends a session. The session's data is preserved in the database but the session is marked as ended and no further messages can be sent to it.

**Response body (`data` field):**

```typescript
{
  sessionId: string;
  // UUID of the ended session.

  ended: true;
  // Confirmation that the session was ended.
}
```

### Endpoint: POST /api/sessions/:id/message

Sends a chat message to a session and returns the full agent response synchronously. This endpoint blocks until the agent has finished processing the message, including all tool calls and reasoning steps.

**Request body:**

```json
{
  "content": "The message text to send to the agent"
}
```

The `content` field is required. Returns 400 with `{ ok: false, error: "content required" }` if missing. Returns 400 with `{ ok: false, error: "Invalid JSON body" }` if the request body is not valid JSON.

**Response body (`data` field):**

```typescript
{
  text: string;
  // The agent's complete response text.

  usage: {
    promptTokens: number;
    // Number of prompt tokens consumed for this response.

    completionTokens: number;
    // Number of completion tokens generated for this response.
  };
}
```

**Error:** Returns 500 with `{ ok: false, error: "Agent error: <description>" }` if the agent encounters an unrecoverable error during processing.

This endpoint is useful for simple integrations that do not need real-time streaming. For real-time streaming of the agent's response, use the WebSocket protocol described below.

### Endpoint: GET /api/skills

Lists all skills with their activation status.

**Response body (`data` field):**

```typescript
Array<{
  name: string;
  // Skill name, including directory prefix. Example: "dramatizer/pipeline".

  description: string;
  // Human-readable description of the skill.

  triggers: string[];
  // Trigger patterns that activate this skill.

  active: boolean;
  // Whether the skill is currently active in the agent's context.

  autoload: boolean;
  // Whether the skill is automatically loaded on startup.
}>
```

### Endpoint: POST /api/skills/:name/activate

Activates a skill by name. The skill name in the URL must be URL-encoded if it contains special characters.

**Response body (`data` field):**

```typescript
{
  name: string;
  // Name of the activated skill.

  activated: true;
  // Confirmation that the skill was activated.
}
```

### Endpoint: GET /api/memory/:type

Reads one of the agent's memory files (MEMORY.md, SOUL.md, or USER.md).

The `:type` parameter must be one of: `MEMORY`, `SOUL`, `USER` (case-insensitive).

**Response body (`data` field):**

```typescript
{
  type: string;
  // The memory type (uppercase): "MEMORY", "SOUL", or "USER".

  content: string;
  // The full text content of the memory file.
  // Empty string if the file does not exist.
}
```

**Error:** Returns 400 with `{ ok: false, error: "Invalid memory type. Use: MEMORY, SOUL, USER" }` if the type parameter is not one of the three valid values.

## WebSocket Protocol

The WebSocket endpoint provides real-time bidirectional communication for interactive chat. Unlike the REST API's `POST /api/sessions/:id/message` endpoint, which blocks until the full response is ready, the WebSocket protocol delivers incremental text, tool progress, and thinking events as they occur.

### Connection Endpoint

```
ws://localhost:3100/ws
wss://host:port/ws     (when behind TLS termination)
```

The WebSocket upgrade is handled by Bun's native WebSocket support via `server.upgrade(req)`. No authentication is currently required for WebSocket connections (the upgrade request is not routed through the API auth middleware). Future versions will add token-based WebSocket authentication.

### Connection Lifecycle

1. **Open.** When a client connects, the server assigns a unique client ID (`ws-1`, `ws-2`, etc.) and registers the client in the connection map. The server tracks which session each client is associated with.

2. **Message handling.** The server parses each incoming message as JSON and dispatches based on the `type` field. Invalid JSON triggers an error response. Unknown message types trigger an error response.

3. **Close.** When a client disconnects (browser tab closed, network failure, explicit close), the server removes the client from the connection map. Active sessions are not automatically ended when a client disconnects -- the session persists in the database and can be resumed by a new connection.

4. **Auto-reconnect (client-side).** The web client's `useWebSocket` hook automatically reconnects 3 seconds after a disconnection. This handles transient network interruptions transparently.

### Client-to-Server Message Types

All client-to-server messages are JSON objects with a `type` field indicating the message type.

#### message -- Send Chat Message

```typescript
{
  type: "message";
  sessionId: string;
  // UUID of the session to send the message to.
  // The session must have been created previously via create_session.

  content: string;
  // The user's message text. Must be non-empty.
}
```

Both `sessionId` and `content` are required. If either is missing, the server responds with an error message: `{ type: "error", message: "sessionId and content required" }`.

When a message is received, the server calls `loop.handleMessage(content, sessionId)` and streams the agent's response back through server-to-client messages (text, tool_progress, thinking, done).

#### create_session -- Create New Session

```typescript
{
  type: "create_session";
  title?: string;
  // Optional session title. If omitted, defaults to "New Session".
}
```

On success, the server responds with `{ type: "session_created", sessionId: "<uuid>" }` and associates the calling client with the new session. On failure, responds with `{ type: "error", message: "Failed to create session: <description>" }`.

#### end_session -- End Session

```typescript
{
  type: "end_session";
  sessionId: string;
  // UUID of the session to end.
}
```

On success, the server responds with `{ type: "session_ended", sessionId: "<uuid>" }`. On failure, responds with `{ type: "error", message: "Failed to end session: <description>" }`.

### Server-to-Client Message Types

All server-to-client messages are JSON objects with a `type` field indicating the message type.

#### session_created

```typescript
{
  type: "session_created";
  sessionId: string;
  // UUID of the newly created session.
}
```

Sent in response to a `create_session` client message.

#### session_ended

```typescript
{
  type: "session_ended";
  sessionId: string;
  // UUID of the ended session.
}
```

Sent in response to an `end_session` client message.

#### text -- Incremental Assistant Text

```typescript
{
  type: "text";
  content: string;
  // Incremental text fragment from the agent's response.
  // The full response is reconstructed by concatenating all text
  // fragments received between the user's message and the done event.
}
```

Multiple `text` messages are sent during a single response as the agent generates text. The web client accumulates these fragments in a ref (`pendingAssistantRef`) and updates the displayed message after each fragment.

#### tool_progress -- Tool Execution Update

```typescript
{
  type: "tool_progress";
  toolName: string;
  // Name of the tool being executed. Example: "cli_run", "bash",
  // "dramatizer_get_artifact".

  status: "running" | "done" | "error";
  // Current status of the tool execution.
  // "running": tool execution has started.
  // "done": tool execution completed successfully.
  // "error": tool execution failed.

  result?: string;
  // Tool execution result. Present when status is "done" or "error".
  // Contains the tool's output or error message.
}
```

The agent may execute multiple tools during a single response. Each tool execution produces at least two `tool_progress` messages: one with status `"running"` when execution starts, and one with status `"done"` or `"error"` when execution completes.

#### thinking -- Agent Thinking Process

```typescript
{
  type: "thinking";
  content: string;
  // Text from the agent's thinking/reasoning process.
  // Currently not displayed in the web client (the handler is a no-op),
  // but available for debugging and future UI features.
}
```

#### done -- Response Complete

```typescript
{
  type: "done";
  usage: {
    promptTokens: number;
    // Total prompt tokens consumed for this response.

    completionTokens: number;
    // Total completion tokens generated for this response.
  };
}
```

Sent exactly once at the end of each agent response. The web client uses this event to clear the loading state, reset active tool indicators, and reset the pending text accumulator.

#### error -- Error Occurred

```typescript
{
  type: "error";
  message: string;
  // Human-readable error description.
  // Examples: "Invalid JSON", "sessionId and content required",
  // "Agent error: <description>", "Unknown message type".
}
```

Sent when the server encounters an error processing a client message. The web client displays error messages as assistant messages with bold "Error:" prefix.

## Web Client

The web client is a lightweight React application that provides a chat interface for interacting with mobai-agent through the server layer. It is served as static files from the `web/dist/` directory by the same HTTP server that hosts the REST API and WebSocket endpoint.

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Vite | 6 | Build tool and development server |
| React | 19 | UI framework |
| TailwindCSS | 3.4 | Utility-first CSS framework |
| react-markdown | 9 | Markdown rendering in assistant messages |
| TypeScript | (latest) | Type safety |

### Directory Structure

```
web/
  index.html                 # HTML entry point
  package.json               # Dependencies: vite, react, tailwindcss, react-markdown
  vite.config.ts             # Vite build configuration
  tsconfig.json              # TypeScript configuration
  src/
    main.tsx                 # React app entry point (ReactDOM.createRoot)
    App.tsx                  # Main layout, session state, WS message dispatch
    types.ts                 # WsClientMessage, WsServerMessage, ChatMessage, SessionInfo
    styles.css               # Tailwind directives + markdown-body + scrollbar styles
    components/
      ChatView.tsx           # Scrollable message list with loading indicator
      InputBar.tsx           # Textarea with Enter/Shift+Enter and auto-resize
      MessageBubble.tsx      # Individual message with user/assistant styling
      SessionList.tsx        # Sidebar with session list and new-session button
      ToolStatus.tsx         # Running tool indicators with spinner
    hooks/
      useWebSocket.ts        # WebSocket connection, state tracking, auto-reconnect
  dist/                      # Build output (served by HTTP server)
```

### Component Details

**App.tsx** is the root component. It manages all application state: the list of sessions (`sessions`), the currently active session ID (`activeSessionId`), the message list for the active session (`messages`), loading state (`isLoading`), and the list of currently executing tools (`activeTools`). It establishes the WebSocket connection via the `useWebSocket` hook, handles incoming server messages through a `handleServerMessage` callback that dispatches on message type, and provides `handleSend`, `handleNewSession`, and `handleSelectSession` callbacks to child components. On mount, it fetches the session list from `GET /api/sessions` via the REST API.

The WebSocket URL is constructed dynamically from the current page's location: `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`. This ensures the WebSocket connects to the same host that served the page, regardless of whether the page is accessed via HTTP or HTTPS.

**ChatView.tsx** renders the scrollable message list. Each message is rendered as a `MessageBubble` component. The component auto-scrolls to the bottom when new messages arrive or when the loading state changes, using a ref on a sentinel `<div>` at the bottom of the list and `scrollIntoView({ behavior: "smooth" })`. When there are no messages, it displays a centered empty state with the agent's name and description.

**InputBar.tsx** provides the text input area. It renders a `<textarea>` (not an `<input>`, to support multi-line messages) with a Send button. The textarea auto-resizes up to a maximum height of 160 pixels based on content. Enter submits the message. Shift+Enter inserts a newline. The input is disabled and shows "Waiting for response..." placeholder text when the agent is processing a response or the WebSocket is disconnected.

**MessageBubble.tsx** renders individual messages with role-specific styling. User messages are displayed with a blue background (`bg-blue-600`) aligned to the right. Assistant messages are displayed with a dark gray background (`bg-gray-800`) aligned to the left, with a border (`border-gray-700`). User message content is rendered as plain text with `whitespace-pre-wrap`. Assistant message content is rendered through `react-markdown` for full Markdown support (headings, code blocks, lists, tables, links). Below the message content, tool progress indicators are displayed if any tools were executed during the response: a yellow gear icon for running tools, a green checkmark for completed tools, and a red X for failed tools, each with the tool name in monospace font.

**SessionList.tsx** renders the sidebar. It has a fixed width of 224 pixels (`w-56`) with a gray-900 background. The header shows "Sessions" with a "+ New" button. Each session is a clickable button showing the session title (truncated with `truncate` class) and the first 8 characters of the session ID. The active session is highlighted with a lighter background (`bg-gray-800`). Empty state shows "No sessions" in centered gray text.

**ToolStatus.tsx** renders the currently executing tools strip between the message list and the input bar. Only "running" tools are displayed. Each tool is shown with a spinning gear icon and the tool name in monospace font, all in yellow-400 color. The component returns null when there are no running tools, collapsing completely out of the layout.

### useWebSocket Hook

The `useWebSocket` hook in `web/src/hooks/useWebSocket.ts` manages the WebSocket connection lifecycle. It exposes:

- **`state: ConnectionState`** -- One of `"connecting"`, `"connected"`, or `"disconnected"`. The App component uses this to show a status indicator (green dot for connected, yellow pulsing dot for connecting, red dot for disconnected) and to disable the input bar when not connected.

- **`lastMessage: WsServerMessage | null`** -- The most recently received server message. The App component watches this with a `useEffect` hook and dispatches to `handleServerMessage` when it changes.

- **`send(msg: WsClientMessage): void`** -- Sends a message to the server. Silently drops the message if the WebSocket is not in the OPEN state.

- **`disconnect(): void`** -- Manually closes the WebSocket connection and cancels auto-reconnect.

Auto-reconnect logic: when the WebSocket closes (whether from server disconnect, network failure, or error), the hook schedules a reconnection attempt after 3 seconds using `setTimeout`. This timer is canceled if the component unmounts or if `disconnect()` is called explicitly. There is no exponential backoff or reconnection limit -- the hook will keep trying to reconnect every 3 seconds indefinitely.

### Build and Development

**Production build:**

```bash
cd web && npm install && npm run build
```

This produces optimized static files in `web/dist/`. The HTTP server automatically serves these files when the directory exists.

**Development mode:**

```bash
cd web && npm run dev
```

This starts the Vite development server on port 5173 with hot module replacement. The Vite configuration proxies `/api/*` and `/ws` requests to the mobai-agent server at `http://localhost:3100`, allowing the web client to be developed with instant reload while communicating with a running server instance.

### Styling

The web client uses a dark theme throughout. The root background is `gray-950` (near-black). The header bar is `gray-900`. The sidebar is `gray-900` with a `gray-800` border. Message bubbles use `gray-800` (assistant) and `blue-600` (user). Input areas use `gray-800`.

Custom CSS in `styles.css` covers three areas:

1. **Markdown body styles.** The `.markdown-body` class applies styling to all Markdown elements rendered by react-markdown: heading sizes and weights, paragraph spacing and line height, list indentation and bullet styles, inline code with green-400 color on gray-800 background, code blocks with gray-900 background and horizontal overflow scrolling, blockquote with left border and italic styling, table borders and header background, and link color in blue-400 with underline.

2. **Scrollbar customization.** WebKit scrollbars are narrowed to 6 pixels, with transparent track and rounded gray-700 thumb.

3. **Tailwind directives.** The standard `@tailwind base`, `@tailwind components`, `@tailwind utilities` imports.

## Implementation

### Server Architecture (src/server/http.ts)

The server is built on `Bun.serve()` with native WebSocket support. The single `Bun.serve()` call handles HTTP requests, WebSocket upgrades, and WebSocket messages in a unified server instance.

The `fetch` handler processes requests in the following priority order:

1. **CORS preflight.** `OPTIONS` requests on any path return 200 with CORS headers.
2. **WebSocket upgrade.** Requests to `/ws` are upgraded to WebSocket connections via `server.upgrade(req)`.
3. **API routes.** Requests with paths starting with `/api/` are authenticated (Bearer token check) and dispatched to the route handler created by `createRouter()`.
4. **Static files.** All other requests are served from `web/dist/` (if the directory exists) with MIME type detection and SPA fallback.
5. **Fallback HTML.** If `web/dist/` does not exist, the root path `/` returns a simple HTML page with instructions to build the web client. All other paths return 404.

### Static File Serving

The `serveStatic()` function serves files from the `web/dist/` directory with the following behavior:

**Path mapping:** The root path `/` is mapped to `/index.html`. All other paths are used as-is.

**Directory traversal prevention:** The resolved file path must start with the `distDir` prefix. If the resolved path escapes the dist directory (via `../` or other path traversal), the server returns 403 (Forbidden).

**MIME type detection:** The server detects content type from file extensions using a built-in mapping table:

| Extension | Content-Type |
|-----------|-------------|
| `.html` | `text/html` |
| `.js` | `application/javascript` |
| `.css` | `text/css` |
| `.json` | `application/json` |
| `.png` | `image/png` |
| `.svg` | `image/svg+xml` |
| `.ico` | `image/x-icon` |
| `.woff2` | `font/woff2` |
| `.woff` | `font/woff` |
| `.map` | `application/json` |

Files with unrecognized extensions are served with `application/octet-stream`.

**SPA fallback:** If the requested path does not match any file in the dist directory, the server returns `index.html` instead of 404. This enables client-side routing in the React application -- the React router handles paths like `/sessions/abc123` on the client side, even though no such file exists on the server.

### WebSocket Handler (src/server/ws-handler.ts)

The WebSocket handler maintains a connection map (`Map<string, WsClient>`) that tracks all connected clients. Each client entry stores the WebSocket reference and the associated session ID (null until the client creates or selects a session).

Message handling is asynchronous: the `handleWsMessage` function parses the incoming JSON, dispatches based on message type, awaits the corresponding AgentLoop operation, and sends the result back to the specific client that sent the request. All WebSocket sends are wrapped in try-catch to handle the case where the client disconnects between the operation starting and the response being ready.

The `createWsCallbacks` function creates tool progress and thinking callbacks that forward events to a specific WebSocket client. These callbacks are passed to the AgentLoop so that tool execution events are streamed to the client in real time.

## Related

- [[entities/mobai-agent]]
- [[concepts/four-layer-philosophy]]
- [[concepts/cli-gateway-protocol]]
- [[syntheses/cloud-deployment-architecture]]

## Sources

- [CLI Gateway + Server Layer Design Spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
