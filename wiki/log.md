---
title: Operation Log
---

# Wiki Operation Log

<!-- Append-only. Each entry: [YYYY-MM-DD HH:MM] ACTION: description -->

[2026-04-14 00:00] INIT: Wiki initialized
[2026-04-14 15:30] INGEST: 7 raw source documents from mobai-agent (design spec, memory, soul, skills)
[2026-04-14 15:30] CREATE: entities/mobai-agent — Master AI agent orchestrator
[2026-04-14 15:30] CREATE: entities/dramatizer — Go novel-to-screenplay pipeline
[2026-04-14 15:30] CREATE: entities/agent-forge — Next.js video production platform
[2026-04-14 15:30] CREATE: entities/moonshort-backend — Next.js game engine
[2026-04-14 15:30] CREATE: entities/moonshort-client — Cocos game frontend
[2026-04-14 15:30] CREATE: entities/cli-gateway — Remote CLI execution microservice
[2026-04-14 15:30] CREATE: concepts/four-layer-philosophy — SKILL/CLI/MCP/API framework
[2026-04-14 15:30] CREATE: concepts/cli-gateway-protocol — HTTP protocol spec
[2026-04-14 15:30] CREATE: concepts/server-layer — mobai-agent HTTP/WS server
[2026-04-14 15:30] CREATE: syntheses/cloud-deployment-architecture — Distributed deployment analysis
[2026-04-14 15:30] UPDATE: index.md — Full table of contents (6 entities, 3 concepts, 1 synthesis)
[2026-04-14 16:30] UPDATE: ALL 10 wiki pages rewritten to reference-grade documentation (2428→4028 lines)
[2026-04-14 16:30] UPDATE: schema.md — Added Documentation Quality Standard (mandatory completeness rules, product vs technical doc separation, length guidelines)
[2026-04-15 18:00] CREATE: entities/moonshort-script — MSS interpreter entity (architecture, CLI, JSON output, file structure, system relationships)
[2026-04-15 18:00] CREATE: concepts/mss-format — MoonShort Script format specification (complete syntax, all directives, Remix compatibility)
[2026-04-15 18:00] UPDATE: index.md — Added moonshort-script entity and mss-format concept
[2026-04-15 19:00] INGEST: 4 raw source documents (product strategy, onboarding guide, unfolded presentation, strategy)
[2026-04-15 19:00] CREATE: syntheses/product-strategy-decisions — 产品战略决策记录（AI Native、D20+Reroll、双Feed、CCR传播）
[2026-04-15 19:00] CREATE: syntheses/platform-onboarding-guide — MobAI 平台全景指南（玩家旅程、数值系统、技术架构）
[2026-04-15 19:00] CREATE: concepts/unfolded-visual-novel — Unfolded 风格展示形态（画布分层、叙事容器、素材管线）
[2026-04-15 19:00] CREATE: plan.md — 团队行动计划（持续维护，产品/技术/运营三线）
[2026-04-15 19:00] UPDATE: index.md — Added plan, 2 syntheses, 1 concept (total: 7 entities, 5 concepts, 3 syntheses, 1 plan)
[2026-04-23 22:50] INGEST: raw/2026-04-23-novel-game-config-design.md (per-novel attribute system design, 5-phase migration landed on moonshort-backend main)
[2026-04-23 22:50] CREATE: concepts/novel-game-config — 每部剧本可配置的属性系统（SAN-slot + 4 检定变量 + 平台级数值整理）
[2026-04-23 22:50] UPDATE: index.md — Added concepts/novel-game-config (total: 7 entities, 6 concepts, 3 syntheses, 1 plan)
[2026-04-24 00:00] INGEST: 2026-04-23-signal-int-backend-design.md
[2026-04-24 00:00] CREATE: concepts/signal-int-backend — MSS @signal int 后台支持（schema/eval/executor/admin 面板）
[2026-04-24 00:30] UPDATE: concepts/signal-int-backend — drop admin panel / cheat endpoint sections (reverted in backend); rewrite as "zero HTTP entrypoint" principle with pivot record
