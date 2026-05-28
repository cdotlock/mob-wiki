---
title: Wiki Index
updated: 2026-05-24
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
- [[concepts/assetctl-integration-contract]] — assetctl 原子能力 CLI 接口合同 v0.1.0：codex 外围编排 + 冻结信封/退出码合同 + 18 颗 ATOMIC_TOOL_IDS（本轮仅 oss-put 可跑，余 NOT_IMPLEMENTED 桩）；assets-produce@48e6eb9 行为基准，全 Go 重写吸收进 IDE，foundation 已合并 main
- [[concepts/assetctl-skills-sync-and-staging]] — Block 2 + Block 3 codex skill 加载链路：assetctl skills load CLI + IDE stageSkills Langfuse-first overlay + IDE-host TTL cache + 静默回退本地 git；S1-S4 共 23 commit 合 main @ 266cd3c
- [[concepts/assets-produce-ide-workspace-contract]] — assets-produce ↔ Moonshort IDE 工作区契约：mapping.json 为唯一契约、assets/ 按 kind 分子目录、新素材自动登记、走 mapping 解析（本地/OSS）；跨机器/Notion/IDE 本体不在职责内
- [[concepts/cg-pipeline]] — novels-to-moonscript stage 07.5 CG pipeline: three-layer flow (cg_collector → cg_render → dramatizer mapping) for `@cg show` MSS directives
- [[concepts/cli-gateway-protocol]] — Unified HTTP protocol for remote CLI command execution
- [[concepts/codex-runtime-and-verification-layers]] — Moonshort IDE 里 codex 怎么起、auth 怎么传（`MOONSHORT_AGENT_API_KEY` + 本地 `codex-shim` HTTP bridge，**不**走 `~/.codex/auth.json`）；4 层验证（L0 单测 / L1a 离线 skill discovery / L1b Langfuse overlay / L2 LLM-in-the-loop）+ 每层跑法 + 代码参考表
- [[concepts/comfyui-modal-deploy]] — ComfyUI on Modal serverless deploy for assetctl `matting` (BiRefNet_toonOut) + `upscale-image` (Real-ESRGAN-anime)；单 Modal app 双 endpoint、阿里云 OSS 直传、IDE 端零改动只改 4 个 FC_* env var；spec 落在 `docs/design/2026-05-21-comfyui-modal-deploy-spec.md`
- [[concepts/dream-rec-component-1-tirt-estimator]] — dream-rec C1: Bayesian TIRT estimator. Laplace MAP + (user, story) testlet random effect + LLM-confidence-weighted ψ² uniqueness. Replaces the choice-count stub.
- [[concepts/dream-rec-component-3-genre-projection]] — dream-rec C3: per-genre projection matrix `M_g` (K_genre × K_global). Hybrid manual-seed + PCA refinement with shadow-swap versioning and identity-on-5-core cold-start fallback.
- [[concepts/dream-rec-component-4-dream-ranker]] — dream-rec C4: axis_match × engagement × freshness additive ranker with continuous sharpness blending. Resolves Component 0 O5; adds `used_cold_start_matrix` to /recommend response.
- [[concepts/dream-rec-component-5-cold-start]] — dream-rec C5: 5-item forced-choice onboarding questionnaire writing informative `(μ₀, Σ₀)` via the same TIRT likelihood. Independent `cold_start_response` table, no `ChoiceEvent` pollution.
- [[concepts/dream-rec-component-6-dashboard]] — dream-rec C6 (deferred): Streamlit dashboard for Loop A/C/B observability. Design locked, implementation awaits `recommend_log` + moonshort funnel API.
- [[concepts/dream-rec-monorepo-migration]] — dream-rec 2026-05-24 monorepo migration: subtree merged into `cdotlock/moonshort-backend → services/dream-rec/` with full history preserved; Dockerfile + dev compose + env keys landed; PR [#4](https://github.com/cdotlock/moonshort-backend/pull/4) open, Railway service provisioning still pending ops.
- [[concepts/dream-rec-trigger-v2-coexistence]] — Scope split between dream-rec (content-ranking) and dream trigger v2 (dream-timing): asset-by-asset decision matrix, three integration commits in `/tmp/msb-dream-rec` (not pushed), deferred items (event weight surface, cross-service vector read).
- [[concepts/dream-trigger-v2-mechanical]] — Producer-side dream trigger v2 (2026-05-21): pure-mechanical evaluator (no LLM) — UserNovelProfile vector + weighted running mean + cosine drift + sharpness gates, replaces v1 single-gate. Drops phase dedup; first-dream保送 keeps committed_success ≥ 3.
- [[concepts/dreaming-universe]] — 玩家画像触发的共享 Dream 支线宇宙：Episode graph + assignment-gated overlay + Python dream-agent
- [[concepts/four-layer-philosophy]] — SKILL / CLI / MCP / API design framework for agent-operated platforms
- [[concepts/moonshort-ide-ai-integration]] — Moonshort IDE 内 AI 集成架构:为什么改用 Cline 而非 VS Code 原生 chat(被 Copilot 闸住),最终两个表面 —— Tab 补全 + Moonshort Agent
- [[concepts/mss-format]] — MoonShort Script (MSS) 脚本标记语言完整规范
- [[concepts/novel-dream-artifact]] — `NovelDreamArtifact` 1:1 sidecar of Novel holds `characterArcs` (renamed from `characterBible`) + `assetMapping` + audit meta; 2026-05-24 抽表 to separate admin authoritative data from dream-pipeline regenerable derived data
- [[concepts/novel-game-config]] — 每部剧本可配置的属性系统（SAN-slot + 4 检定变量 + 平台级数值整理）
- [[concepts/remix-anywhere]] — 玩家长按对白 → D20+DC → LLM 生成 InsertPatch 插入剧情（含 forward planner 跨集回响）
- [[concepts/server-layer]] — mobai-agent HTTP/WebSocket server for remote access
- [[concepts/sfx-pipeline]] — SFX pipeline design: `sfx-normalizer` skill + dramatizer integration for AI-generated sound effects via ElevenLabs
- [[concepts/signal-int-backend]] — Backend 如何加载、持久化、求值、管理 MSS 的 `@signal int` 作者变量
- [[concepts/stable-step-id]] — 内容寻址 cursor：每个 MSS step 编译期带稳定 ID，splice/replace 对 cursor 透明
- [[concepts/unfolded-visual-novel]] — Unfolded 风格互动视觉小说展示形态与素材管线

## Entities

- [[entities/agent-forge]] — Next.js video production platform with 48 MCP tools
- [[entities/assets-produce]] — Agent-native asset production platform with local prompt workflow knowledge and opencode `videoctl`
- [[entities/cli-gateway]] — Lightweight HTTP microservice for remote CLI execution (deployed per-service)
- [[entities/dramatizer]] — Go binary for novel-to-screenplay conversion (15-stage LLM pipeline)
- [[entities/dramatizer-mss]] — Novels-to-Moonscript skill workflow for MSS writing, route planning, and visual asset production
- [[entities/mob-ai-router]] — Public OpenAI-compatible LLM router (`https://ai.mob-ai.cn/api`) fronting Claude, DeepSeek, GPT, Jina embeddings/rerank, and image/video providers behind a single virtual-key surface
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
