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
[2026-05-20 02:44] CREATE: concepts/assetctl-integration-contract — assetctl 原子能力 CLI 冻结接口合同 v0.1.0（信封/退出码/18-id 目录/oss-put 唯一可跑）、assets-produce@48e6eb9 基准、全 Go 重写落地与 foundation 完成状态（已合并 moonshort-ide main @3b70daa）
[2026-05-20 02:44] UPDATE: index.md — registered concepts/assetctl-integration-contract; bump updated date to 2026-05-20
[2026-05-20 12:00] UPDATE: concepts/assetctl-integration-contract — Wave 1 完成（W1-1..5；17 atomic commit；4 颗 runnable：oss-put + nanobanana + seedance + sfxelevenlabs；共享件 internal/aliyun + internal/fc；jsonschema 扩展 Number/Array/Pattern；iface.Tool.MissingEnv 接口加宽；合并 moonshort-ide main @c7e7f0c；覆盖率全部 ≥87%，多颗 100%；pnpm lint/typecheck/go:test 全过）
[2026-05-20 16:30] UPDATE: concepts/assetctl-integration-contract — Wave 2 完成（W2-1..5；10 atomic commit feat 7/refactor 3；5 颗新 runnable：generate-image-gpt + generate-video-happyhorse + generate-music-suno + concat-clips + crop-video；总 runnable 升至 9 颗，余 9 Python 桩；jsonschema 扩展 Enum + ObjectProp 嵌套对象 items；合并 moonshort-ide main @b8b7f94；新工具覆盖率 gpt/concatclips/cropvideo/suno 100%、happyhorse 94.3%、jsonschema 99.1%；pnpm lint/typecheck/go:test 全过）
[2026-05-20 18:00] UPDATE: concepts/assetctl-integration-contract — Wave 3 完成（W3-1..5；10 atomic commit feat 5/refactor 4/docs 1；3 颗新 runnable Pattern E：cutout + green-spill-clear + rgb-unspill；总 runnable 升至 12 颗，余 6 F-stub；新共享层 internal/imageio：PIL-兼容 RGBToHSV + GaussianBlurAlpha + PNG I/O wrappers；合并 moonshort-ide main @bea7017；新工具与 imageio 覆盖率 90.3%–92.3%；Wave 4 stub 升级评估 doc 同步上 main；pnpm lint/typecheck/go:test 全过）
[2026-05-20 22:30] UPDATE: concepts/assetctl-integration-contract — Wave 4 stub 升级评估闭环（不实现工具只做评估；docs/design/2026-05-20-assetctl-wave4-stub-upgrade-evaluation.md @ moonshort-ide main 14594de；W4-1 chai2010/webp PoC 实跑：macOS arm64 native ✅ 通过、binary 3.8 MB、72-byte 有效 VP8 输出、linux 跨编译 ❌ 需 zig/musl-cross 工具链；W4-1 = 最低成本 F→E 候选解锁 hybrid-to-webp + rgb-unspill .webp 两颗能力；W4-2/W4-3 gocv/onnxruntime_go PoC 留待业务驱动启动；Wave 4 = evaluation-only wave，闭环作为 Wave 5+ 实施决策输入）
[2026-05-20 23:45] UPDATE: concepts/assetctl-integration-contract — Wave 5 完成（W5-1..5；10 atomic commit plan 1/feat 4/refactor 3/test 1/build 1；1 颗新 runnable Pattern E2：hybrid-to-webp，1 颗 W3 工具扩 .webp 输出：rgb-unspill；总 runnable 升至 13 颗，余 5 F-stub；新共享层 internal/webpio：WriteWebP + WritePlaceholderWebP + WriteOptions，含 nrgbaToRGBA helper 避开 chai2010/webp 慢路径；assetctl 首个 cgo 依赖 github.com/chai2010/webp v1.4.0 自带 libwebp C 源；fork/build.mjs buildAssetctl 加 CGO_ENABLED=1 + zig cc 跨编译，ZIG_TARGETS 覆盖 linux/amd64/arm64 + windows/amd64，macOS host→macOS 无需 zig；合并 moonshort-ide main @8900997；webpio/hybridtowebp/rgbunspill 覆盖率 91.7%–94.4%；跨编译 smoke 三目标全通：macOS arm64 11.6MB Mach-O / linux amd64 18.8MB / linux arm64 18.1MB 静态 ELF；pnpm lint/typecheck/go:test 全过）
