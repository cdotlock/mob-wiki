---
title: Wiki Index
updated: 2026-05-12
---

# Mob-Wiki Index

Welcome to the team knowledge base.

## Plan

- [[plan]] — 团队行动计划（持续维护，所有人可更新进度）

## Concepts

- [[concepts/asset-matting-hybrid]] — novels-to-moonscript / asset-renderer 抠图流水线：A 默认 (chromakey) + 检测 + B 兜底 (MODNet)，11 张 A/B 实验数据 + 4 个独立 CLI 架构
- [[concepts/asset-pipeline-aspect-ratio-recovery-2026-05]] — NRBI 2026-05 asset pipeline drift root-cause + recovery playbook: mob-ai aspect-ratio non-determinism, render-without-resync footgun, cascade re-render strategy
- [[concepts/asset-pipeline-green-spill-fix-2026-05-09]] — green-spill root cause + RGB unspill fix landed 2026-05-09 (renderer level patch, not matting workaround)
- [[concepts/asset-pipeline-green-spill-runbook]] — green-spill follow-up runbook: recipes for re-render / verify / batch passes referencing the 05-09 fix
- [[concepts/cli-gateway-protocol]] — Unified HTTP protocol for remote CLI command execution
- [[concepts/dreaming-universe]] — 玩家画像触发的共享 Dream 支线宇宙：Episode graph + assignment-gated overlay + Python dream-agent
- [[concepts/four-layer-philosophy]] — SKILL / CLI / MCP / API design framework for agent-operated platforms
- [[concepts/mss-format]] — MoonShort Script (MSS) 脚本标记语言完整规范
- [[concepts/novel-game-config]] — 每部剧本可配置的属性系统（SAN-slot + 4 检定变量 + 平台级数值整理）
- [[concepts/remix-anywhere]] — 玩家长按对白 → D20+DC → LLM 生成 InsertPatch 插入剧情（含 forward planner 跨集回响）
- [[concepts/server-layer]] — mobai-agent HTTP/WebSocket server for remote access
- [[concepts/signal-int-backend]] — Backend 如何加载、持久化、求值、管理 MSS 的 `@signal int` 作者变量
- [[concepts/stable-step-id]] — 内容寻址 cursor：每个 MSS step 编译期带稳定 ID，splice/replace 对 cursor 透明
- [[concepts/unfolded-visual-novel]] — Unfolded 风格互动视觉小说展示形态与素材管线

## Entities

- [[entities/agent-forge]] — Next.js video production platform with 48 MCP tools
- [[entities/assets-produce]] — Agent-native asset production platform with local prompt workflow knowledge and opencode `videoctl`
- [[entities/cli-gateway]] — Lightweight HTTP microservice for remote CLI execution (deployed per-service)
- [[entities/dramatizer]] — Go binary for novel-to-screenplay conversion (15-stage LLM pipeline)
- [[entities/dramatizer-mss]] — Novels-to-Moonscript skill workflow for MSS writing, route planning, and visual asset production
- [[entities/mob-mini-agent]] — Pi-based company Agent foundation with Moonshot runtime practices, observability, and compaction safety
- [[entities/mob-sandbox-ops]] — Self-hosted Daytona/OpenHands/Claude Code sandbox platform and operator runbook
- [[entities/mobai-agent]] — Master AI agent orchestrator for the Moonshort platform
- [[entities/moonshort-backend]] — Next.js game engine, admin dashboard, 85+ API routes
- [[entities/moonshort-client]] — Cocos Creator game frontend with headless testing
- [[entities/moonshort-script]] — MSS interpreter: Go binary compiling .md scripts to player-ready JSON
- [[entities/video-agent-claude-wangbo]] — Claude Code video shot prompt workflow with Seedance gateway, OSS validation, and ablation-backed skill package

## Syntheses

- [[syntheses/cloud-deployment-architecture]] — How Moonshort transitions from local to distributed cloud deployment
- [[syntheses/platform-onboarding-guide]] — MobAI 平台全景指南（游戏设计、数值系统、技术架构）
- [[syntheses/product-strategy-decisions]] — 产品战略决策记录（为什么这样做而不是那样做）
- [[syntheses/render-time-silent-drop-failure-class]] — VN Pipeline v4.1-v4.5 同构族（branch-architect + episode-writer 的"schema 正确 + render 丢规则"反复 bug 及四件套沉淀模式，含 v4.4/v4.5 结构对偶：first-contact vs last-contact agency）
