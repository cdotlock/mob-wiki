---
title: mobai-agent Server Layer
tags: [http, websocket, api, web-client]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

HTTP/WebSocket server layer for [[entities/mobai-agent]] that enables remote access from web clients and other systems. Replaces the terminal-only TUI with a network-accessible interface while keeping the same AgentLoop core.

## Activation

```bash
bun run dev -- --server --port 3100
# Or in config.yaml:
# server:
#   enabled: true
#   port: 3100
```

## REST API

All endpoints under `/api/`, authenticated via `Authorization: Bearer <MOBAI_API_KEY>`.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Status, uptime, tool count, active skills |
| `POST` | `/api/sessions` | Create session |
| `GET` | `/api/sessions` | List sessions |
| `GET` | `/api/sessions/:id` | Session details + messages |
| `DELETE` | `/api/sessions/:id` | End session |
| `POST` | `/api/sessions/:id/message` | Send message (sync response) |
| `GET` | `/api/skills` | List skills |
| `POST` | `/api/skills/:name/activate` | Activate skill |
| `GET` | `/api/memory/:type` | Read MEMORY/SOUL/USER |

## WebSocket `/ws`

Real-time bidirectional chat streaming.

**Client sends:** `message` (chat), `create_session`, `end_session`
**Server sends:** `text` (incremental), `tool_progress`, `thinking`, `done`, `error`

## Web Client

Lightweight React + TailwindCSS chat interface served from `web/dist/`:
- Session sidebar with create/select
- Markdown-rendered message bubbles
- Tool execution progress indicators
- WebSocket auto-reconnect
- Build: `cd web && npm run build`

## Implementation

Uses `Bun.serve()` with native WebSocket support. Same `AgentLoop` instance as TUI mode. Static files served via SPA fallback for the web client.

## Related

- [[entities/mobai-agent]]
- [[syntheses/cloud-deployment-architecture]]

## Sources

- [Design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
