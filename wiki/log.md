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
[2026-04-27 02:00] INGEST: docs/superpowers/specs/2026-04-26-stable-step-id-design.md (one-shot cutover完成 across moonshort-script + moonshort-backend; dev DB migrated; 11/11 sessions walk via smoke)
[2026-04-27 02:00] CREATE: concepts/stable-step-id — 内容寻址 cursor design + ID format + AchievementStep.id 改名 + migration approach
[2026-04-27 02:00] UPDATE: index.md — registered concepts/stable-step-id (total: 7 entities, 9 concepts, 3 syntheses, 1 plan)
[2026-05-03 16:03] CREATE: entities/video-agent-claude-wangbo — 视频分镜 prompt skill、Seedance gateway、OSS URL 验证、消融实验结论
[2026-05-03 16:03] CREATE: concepts/dreaming-universe — Dream 共享支线宇宙、Episode graph + entry overlay、Python dream-agent 当前架构
[2026-05-03 16:03] CREATE: entities/dramatizer-mss — novels-to-moonscript 技能流水线、MSS 写作、Sprite Canonical C' 与 wardrobe canonicalization
[2026-05-03 16:03] UPDATE: entities/moonshort-backend — add Dreaming Universe backend services, internal APIs, env vars, and current persistence gap
[2026-05-03 16:03] UPDATE: entities/mob-sandbox-ops — sync TUI/OpenHands/operator lessons and replace plaintext-secret runbook style with .env references
[2026-05-03 16:03] UPDATE: index.md — register Dreaming Universe, Dramatizer-MSS, mob-sandbox ops, and video agent pages
[2026-05-04 20:45] CREATE: entities/mob-mini-agent — smolagents fork with Mob embedded function-call runtime, subagents, skills, context assembly, LiteLLM, MCP, and FastAPI adapters
[2026-05-04 20:45] UPDATE: index.md — registered mob-mini-agent entity
[2026-05-04 20:55] UPDATE: entities/mob-mini-agent — add default build/plan/explore/general agent profiles as customizable reference cases and update source line count
[2026-05-10 20:30] UPDATE: entities/mob-mini-agent — document runtime hardening, agent-targeted skill autoload, memory compaction, and update source line count
[2026-05-11 14:31] INGEST: raw/2026-05-11-assets-produce-local-videoctl-cleanup.md (assets-produce local videoctl integration, reference folder cleanup, prompt-only knowledge pack)
[2026-05-11 14:31] CREATE: entities/assets-produce — agent-native asset production platform with local novel-to-video knowledge and opencode videoctl
[2026-05-11 14:31] UPDATE: index.md — registered assets-produce entity
[2026-05-12 22:10] UPDATE: entities/mob-mini-agent — sync Pi core transition, foundation package boundary, and production Dream Agent runtime practices
[2026-05-12 22:49] UPDATE: entities/mob-mini-agent — record final Pi-only foundation state, removal of old compatibility surface, run observability diagnostics, and production pitfall rules
[2026-05-14 12:30] CREATE: concepts/asset-pipeline-aspect-ratio-recovery-2026-05 — NRBI 2026-05 aspect-ratio drift root-cause + cascade re-render playbook
[2026-05-14 12:30] CREATE: concepts/asset-pipeline-green-spill-fix-2026-05-09 — green-spill RGB unspill renderer-level fix landed 2026-05-09
[2026-05-14 12:30] CREATE: concepts/asset-pipeline-green-spill-runbook — green-spill follow-up runbook for re-render and verification passes
[2026-05-14 12:30] UPDATE: index.md — registered 3 asset-pipeline concepts (aspect-ratio recovery + green-spill fix + runbook)
[2026-05-14 12:32] CREATE: concepts/cg-pipeline — novels-to-moonscript stage 07.5 three-layer CG pipeline (cg_collector → cg_render → dramatizer mapping)
[2026-05-14 12:32] UPDATE: index.md — registered concepts/cg-pipeline
[2026-05-14 12:34] CREATE: concepts/sfx-pipeline — SFX pipeline design (sfx-normalizer skill + dramatizer integration for ElevenLabs AI sound effects)
[2026-05-14 12:34] UPDATE: index.md — registered concepts/sfx-pipeline
[2026-05-14 12:36] UPDATE: entities/agent-forge — add deprecation banner pointing to assets-produce (opencode-based rewrite); marked tags deprecated, kept page as historical entity
[2026-05-14 12:36] UPDATE: plan.md — "Agent-Forge 转型" status row 改为 "已 fork 重写为 assets-produce, Phase 7 in progress"; 待启动 列表对应任务挂到 assets-produce
[2026-05-14 12:36] UPDATE: index.md — bump updated date to 2026-05-14 after batch ingest
