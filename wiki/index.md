---
title: Wiki Index
updated: 2026-06-06
---

# Mob-Wiki Index

Welcome to the team knowledge base.

## Plan

- [[plan]] — 团队行动计划（持续维护，所有人可更新进度）

## Concepts

- [[concepts/asset-matting-hybrid]] — novels-to-lunascript / asset-renderer 抠图流水线：A 默认 (chromakey) + 检测 + B 兜底 (MODNet)，11 张 A/B 实验数据 + 4 个独立 CLI 架构
- [[concepts/asset-pipeline-aspect-ratio-recovery-2026-05]] — NRBI 2026-05 asset pipeline drift root-cause + recovery playbook: mob-ai aspect-ratio non-determinism, render-without-resync footgun, cascade re-render strategy
- [[concepts/asset-pipeline-green-spill-fix-2026-05-09]] — green-spill root cause + RGB unspill fix landed 2026-05-09 (renderer level patch, not matting workaround)
- [[concepts/asset-pipeline-green-spill-runbook]] — green-spill follow-up runbook: recipes for re-render / verify / batch passes referencing the 05-09 fix
- [[concepts/assetctl-integration-contract]] — assetctl 原子能力 CLI 接口合同 v0.1.0：codex 外围编排 + 冻结信封/退出码合同 + 18 颗 ATOMIC_TOOL_IDS（本轮仅 oss-put 可跑，余 NOT_IMPLEMENTED 桩）；assets-produce@48e6eb9 行为基准，全 Go 重写吸收进 IDE，foundation 已合并 main
- [[concepts/assetctl-skills-sync-and-staging]] — Block 2 + Block 3 codex skill 加载链路：assetctl skills load CLI + IDE stageSkills Langfuse-first overlay + IDE-host TTL cache + 静默回退本地 git；S1-S4 共 23 commit 合 main @ 266cd3c
- [[concepts/assets-produce-ide-workspace-contract]] — assets-produce ↔ Lunaverse IDE 工作区契约：mapping.json 为唯一契约、assets/ 按 kind 分子目录、新素材自动登记、走 mapping 解析（本地/OSS）；跨机器/Notion/IDE 本体不在职责内
- [[concepts/cg-pipeline]] — novels-to-lunascript stage 07.5 CG pipeline: three-layer flow (cg_collector → cg_render → dramatizer mapping) for `@cg show` LS directives
- [[concepts/cli-gateway-protocol]] — Unified HTTP protocol for remote CLI command execution
- [[concepts/codex-runtime-and-verification-layers]] — Lunaverse IDE 里 codex 怎么起、auth 怎么传（`LUNAVERSE_AGENT_API_KEY` + 本地 `codex-shim` HTTP bridge，**不**走 `~/.codex/auth.json`）；4 层验证（L0 单测 / L1a 离线 skill discovery / L1b Langfuse overlay / L2 LLM-in-the-loop）+ 每层跑法 + 代码参考表
- [[concepts/comfyui-modal-deploy]] — ComfyUI on Modal serverless deploy for assetctl `matting` (BiRefNet_toonOut) + `upscale-image` (Real-ESRGAN-anime)；单 Modal app 双 endpoint、阿里云 OSS 直传、IDE 端零改动只改 4 个 FC_* env var；spec 落在 `docs/design/2026-05-21-comfyui-modal-deploy-spec.md`
- [[concepts/dream-bonus-only-op]] — 2026-05-26 dream entry-patch 大改：3 个 v1 ops 全废、单一 `bonus_only` op（terminal placement + template Continue + LLM 写的 ✦DREAM 文案 + 机械路由）；feed 入口直接落 dream E1；no-mainline-mutation invariant（三层 defense：writer/reviewer/backend）
- [[concepts/dream-rec-component-1-tirt-estimator]] — dream-rec C1: Bayesian TIRT estimator. Laplace MAP + (user, story) testlet random effect + LLM-confidence-weighted ψ² uniqueness. Replaces the choice-count stub.
- [[concepts/dream-rec-component-3-genre-projection]] — dream-rec C3: per-genre projection matrix `M_g` (K_genre × K_global). Hybrid manual-seed + PCA refinement with shadow-swap versioning and identity-on-5-core cold-start fallback.
- [[concepts/dream-rec-component-4-dream-ranker]] — dream-rec C4: axis_match × engagement × freshness additive ranker with continuous sharpness blending. Resolves Component 0 O5; adds `used_cold_start_matrix` to /recommend response.
- [[concepts/dream-rec-component-5-cold-start]] — dream-rec C5: 5-item forced-choice onboarding questionnaire writing informative `(μ₀, Σ₀)` via the same TIRT likelihood. Independent `cold_start_response` table, no `ChoiceEvent` pollution.
- [[concepts/dream-rec-component-6-dashboard]] — dream-rec C6 (deferred): Streamlit dashboard for Loop A/C/B observability. Design locked, implementation awaits `recommend_log` + lunaverse funnel API.
- [[concepts/dream-rec-monorepo-migration]] — dream-rec 2026-05-24 monorepo migration: subtree merged into `cdotlock/lunaverse-backend → services/dream-rec/` with full history preserved; Dockerfile + dev compose + env keys landed; PR [#4](https://github.com/cdotlock/lunaverse-backend/pull/4) open, Railway service provisioning still pending ops.
- [[concepts/dream-rec-trigger-v2-coexistence]] — Scope split between dream-rec (content-ranking) and dream trigger v2 (dream-timing): asset-by-asset decision matrix, three integration commits in `/tmp/msb-dream-rec` (not pushed), deferred items (event weight surface, cross-service vector read).
- [[concepts/dream-trigger-v2-mechanical]] — Producer-side dream trigger v2 (2026-05-21): pure-mechanical evaluator (no LLM) — UserNovelProfile vector + weighted running mean + cosine drift + sharpness gates, replaces v1 single-gate. Drops phase dedup; first-dream保送 keeps committed_success ≥ 3.
- [[concepts/dreaming-universe]] — 玩家画像触发的共享 Dream 支线宇宙：Episode graph + assignment-gated overlay + Python dream-agent
- [[concepts/four-layer-philosophy]] — SKILL / CLI / MCP / API design framework for agent-operated platforms
- [[concepts/lunaverse-ide-ai-integration]] — Lunaverse IDE 内 AI 集成架构:为什么改用 Cline 而非 VS Code 原生 chat(被 Copilot 闸住),最终两个表面 —— Tab 补全 + Lunaverse Agent
- [[concepts/ls-format]] — Lunascripts (LS) 脚本标记语言完整规范（2026-06-04 大幅 redesign 后的快照）
- [[concepts/ls-spec-redesign-2026-06]] — LS 2026-06-04 redesign 决策记录：删除 ~半数旧指令冗余（show/hide/look/move/at、@ending、@label/@goto、influence、@cg block、@music play/crossfade/fadeout、@sfx play、@pause for N），新增同屏一人隐式 hide 规则、operand 出现在 comparison 两侧、MAX/MIN 聚合、变量对变量比较；Go 编译器 + 测试 + testdata + skills 全量对齐，5 个 commit pushed to lunascripts@main
- [[concepts/novel-dream-artifact]] — `NovelDreamArtifact` 1:1 sidecar of Novel holds `characterArcs` (renamed from `characterBible`) + `assetMapping` + audit meta; 2026-05-24 抽表 to separate admin authoritative data from dream-pipeline regenerable derived data
- [[concepts/novel-game-config]] — 每部剧本可配置的属性系统（SAN-slot + 4 检定变量 + 平台级数值整理）
- [[concepts/otome-script-quality-evaluator]] — 乙女逐剧本质量评分器设计（per-script quality gate，benchmark 的 ② 层）：输入一篇 LS 剧本 → 输出分维度评分 + 定位问题清单 + PASS/WARN/FAIL；3 层架构（L0 结构客观校验仿 RPGBench / L1 逐场景 LLM 评分仿 HelloEval+RMTBench / L2 全篇一致性仿 ConStory）+ 5 个原创乙女维度 + Phase 0-3 落地分期
- [[concepts/otome-writing-benchmark-survey-2026-06]] — 乙女小说写作 benchmark 调研 + 自建指标草案（2026-06-04 deep-research + 补搜）：现成无乙女专用 benchmark；选模型用 EQ-Bench v3，方法论搬 HelloEval/RMTBench/ConStory/RPGBench；真空白只剩恋爱弧 + 男主魅力，自建只需原创这一层
- [[concepts/production-pipeline-two-phase]] — lunaverse-backend 2026-05 Plan A + C1 重构：IDE submit → admin activate；`Novel.activeReleaseId` 唯一真相；L1/L2/L3 分层；删 `NovelDraftAsset` / `Novel.status` / `NovelCharacter.voiceId` / `characterBible`；release 状态机 `pending` / `live` / `superseded` / `failed`
- [[concepts/railway-production-deploy]] — lunaverse-backend 怎么上 Railway 生产：service 拓扑 + `railway-production-deploy.yml` workflow（confirm/skip_migrations/force_* inputs）+ account-token 鉴权（2026-06-05 CLI 回归 `railway up` 拒 project token 的复盘）+ 为何 skip in-CI migrate（prod 无 `_prisma_migrations` → P3005 + pooler 15-client 上限）+ **additive-only 零删库 cutover playbook**（merged-schema `migrate diff` 证 prod 已是 HEAD 超集 → 不 apply drop）+ 单本免 redeploy re-seed + TTS warmth 行级寻址；2026-06-06 LS realignment 上线为 worked example
- [[concepts/remix-anywhere]] — 玩家长按对白 → D20+DC → LLM 生成 InsertPatch 插入剧情；Drama Remix 2026-05-05 整体摘除；forward planner 2026-05-24 改单 plan + 2-stage pick→write 跨非 dream 全分支
- [[concepts/server-layer]] — mobai-agent HTTP/WebSocket server for remote access
- [[concepts/sfx-pipeline]] — SFX pipeline design: `sfx-normalizer` skill + dramatizer integration for AI-generated sound effects via ElevenLabs
- [[concepts/signal-int-backend]] — Backend 如何加载、持久化、求值、管理 LS 的 `@signal int` 作者变量
- [[concepts/stable-step-id]] — 内容寻址 cursor：每个 LS step 编译期带稳定 ID，splice/replace 对 cursor 透明
- [[concepts/style-langfuse-migration]] — 风格 prompt → Langfuse 权威源迁移（2026-06-02）：16 family style_*、IDE Workshop CRUD UI、render 三层兜底；CF-1010 需 User-Agent + 真凭据在 assets-produce/.env（backend 是占位）；skills-sync 的风格侧同构
- [[concepts/supabase-backend-bootstrap]] — 2026-05-29 backend 生产 Postgres 切 Supabase；fresh-bootstrap 流程（`db push + raw contract SQL`，`BOOTSTRAP_TARGET_DB_NAME` 防呆）；migration 是增量补丁、不支持空库 replay（2026-04-27 option A 决策）；灾备走 DB 备份 / restore
- [[concepts/unfolded-visual-novel]] — Unfolded 风格互动视觉小说展示形态与素材管线
- [[concepts/villain-season-demo]] — 恶人季 Heart Signal NA otome 短剧 demo（3 EP + 1 dream，双语 EN+ZH 平行 novel，autoAssign + bonus_only 强制 dream，22 SFX/7 角色/6 BG/3 BGM，英文 Breeze 配音 + TTS 上 R2，机制全覆盖含 Remix/Dream/signal/affection/butterfly/achievement/trick/minigame）

## Entities

- [[entities/agent-forge]] — Next.js video production platform with 48 MCP tools
- [[entities/assets-produce]] — Agent-native asset production platform with local prompt workflow knowledge and opencode `videoctl`
- [[entities/cli-gateway]] — Lightweight HTTP microservice for remote CLI execution (deployed per-service)
- [[entities/dramatizer]] — Go binary for novel-to-screenplay conversion (15-stage LLM pipeline)
- [[entities/dramatizer-ls]] — Novels-to-Lunascript skill workflow（**2026-05-19 起 upstream authoring 10 skills 整体迁到 assets-produce**；本仓只剩 downstream asset / cg / wardrobe pipeline + NRBI 真实生产工程文件夹）
- [[entities/mob-ai-router]] — Public OpenAI-compatible LLM router (`https://ai.mob-ai.cn/api`) fronting Claude, DeepSeek, GPT, Jina embeddings/rerank, and image/video providers behind a single virtual-key surface
- [[entities/mob-mini-agent]] — Pi-based company Agent foundation with Moonshot runtime practices, observability, and compaction safety
- [[entities/mob-sandbox-ops]] — Self-hosted Daytona/OpenHands/Claude Code sandbox platform and operator runbook
- [[entities/mobai-agent]] — Master AI agent orchestrator for the Lunaverse platform
- [[entities/lunaverse-backend]] — Next.js game engine, admin dashboard, 85+ API routes
- [[entities/lunaverse-client]] — Cocos Creator game frontend with headless testing
- [[entities/lunaverse-ide]] — VS Code 1.119.1 fork 一层壳：LS 编辑 + `ls-lsp` + Production Workshop（6 agents，含 voice casting workbench / onboarding spotlight tour / minigame workbench / production manifest publish）+ codex agent 跑时 + Lunaverse Agent (Cline fork)；8 packages + agents/ 单一 canonical config root
- [[entities/lunascripts]] — LS interpreter: Go binary compiling .md scripts to player-ready JSON；2026-05 trick/minigame 解耦 + trick 白名单锁死 6 类 + minigame 退化为叶子 + FastAPI wrapper + episode-scoped step ID
- [[entities/video-agent-claude-wangbo]] — Claude Code video shot prompt workflow with Seedance gateway, OSS validation, and ablation-backed skill package

## Syntheses

- [[syntheses/cloud-deployment-architecture]] — How Lunaverse transitions from local to distributed cloud deployment
- [[syntheses/lunaverse-rename-migration]] — lunaverse→Lunaverse / LS→Lunascripts / .ls→.ls 全量改名方案：9 仓 ~1万处 + ~575 文件物理改名；扩展名三套并存现状、七桶分类、6 个待拍板决策、带兼容垫片的 7 阶段切换、静默失败清单
- [[syntheses/platform-onboarding-guide]] — MobAI 平台全景指南（游戏设计、数值系统、技术架构）
- [[syntheses/product-strategy-decisions]] — 产品战略决策记录（为什么这样做而不是那样做）
- [[syntheses/render-time-silent-drop-failure-class]] — VN Pipeline v4.1-v4.5 同构族（branch-architect + episode-writer 的"schema 正确 + render 丢规则"反复 bug 及四件套沉淀模式，含 v4.4/v4.5 结构对偶：first-contact vs last-contact agency）
