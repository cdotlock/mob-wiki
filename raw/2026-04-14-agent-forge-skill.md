---
name: agent-forge-video
description: Agent-Forge video production platform — AI-powered novel-to-video pipeline
triggers: ["agent-forge", "video", "视频", "episode", "剧集", "forge", "production", "生产"]
autoload: false
priority: 10
---

# Agent-Forge — Video Production Platform

Agent-Forge orchestrates AI agents and services to automate video creation workflows, transforming stories into video episodes.

## Architecture

- **Server**: Next.js 16 at `http://localhost:8001`
- **MCP**: Connected as `agent-forge` (HTTP) — tools prefixed `agent_forge_`
- **Database**: PostgreSQL via Prisma
- **Storage**: Alibaba Cloud OSS

## MCP Tools Available

Agent-Forge exposes ALL tools + skills as MCP resources. Key tool categories:

### Skills Management
- `agent_forge_skills__list` — List all skills
- `agent_forge_skills__get` — Get specific skill content
- `agent_forge_skills__create` — Create new skill
- `agent_forge_skills__update` — Update skill

### Video Management
- `agent_forge_video_mgr__list_novels` — List available novels
- `agent_forge_video_mgr__list_episodes` — List episodes for a novel
- `agent_forge_video_mgr__create_episode` — Create/update episode
- `agent_forge_video_mgr__get_content` — Get episode content
- `agent_forge_video_mgr__get_resources` — List attached resources
- `agent_forge_video_mgr__get_status` — Check generation status

### Task System (Async)
- `agent_forge_tasks__submit` — Submit async task with message
- `agent_forge_tasks__status` — Query task status
- `agent_forge_tasks__cancel` — Cancel running task

### Agent Chat
- `agent_forge_chat__send` — Send message to agent (synchronous)
- `agent_forge_chat__stream` — Chat with streaming

### Dynamic MCP Tools
- `agent_forge_mcps__list` — List all MCP providers
- `agent_forge_mcps__create` — Create dynamic MCP (JS sandbox)
- `agent_forge_mcps__reload` — Reload MCP provider

## Common Workflows

### Generate Video for a Novel Episode
```
1. agent_forge_video_mgr__list_novels {}
2. agent_forge_video_mgr__list_episodes { novel_id: "..." }
3. agent_forge_tasks__submit { message: "Generate video for episode X of novel Y" }
4. agent_forge_tasks__status { task_id: "..." }  (poll until done)
5. agent_forge_video_mgr__get_resources { script_id: "..." }
```

### Use Agent Chat for Complex Tasks
```
agent_forge_chat__send { message: "Create a new skill for handling character voice consistency" }
```

### Check Task Progress via REST (alternative)
```
bash: curl -s http://localhost:8001/api/tasks/<id>/events
```

## REST API Endpoints (via bash curl)

- `POST /api/tasks` — Submit async task
- `GET /api/tasks/{id}` — Query task status
- `GET /api/tasks/{id}/events` — SSE stream of events
- `POST /api/tasks/{id}/cancel` — Cancel task
- `GET /api/video/novels` — List novels
- `GET /api/video/novels/{id}/episodes` — List episodes
- `POST /api/video/episodes/{id}` — Create/update episode
- `GET /api/video/episodes/{id}/content` — Get content
- `GET /api/video/episodes/{id}/resources` — Get resources
- `GET /api/video/episodes/{id}/status` — Check status

## Key Constraints
- All business logic in service layer — REST and MCP share same functions
- Tasks use SSE streaming for real-time progress
- Dynamic MCPs run in QuickJS WebAssembly sandbox
- Sessions tracked by session_id for multi-turn conversations
- Storage via Alibaba Cloud OSS (images, videos, audio)
