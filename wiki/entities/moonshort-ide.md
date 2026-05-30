---
title: Moonshort IDE
tags: [ide, vscode-fork, mss, cline, codex, assetctl, voice-casting, minigame]
sources: []
created: 2026-05-30
updated: 2026-05-30
---

Moonshort IDE 是给 [[entities/moonshort-script]] 编剧 + 资产生产人员用的桌面应用 —— **VS Code 1.119.1 fork** 一层壳，把 MSS 编辑、`mss-lsp` 语言服务、`mss` 编译器、`videoctl` / `assetctl` 资产 CLI、Moonshort Agent（fork 自 Cline）+ codex agent 跑时、以及 Production Workshop 流水线一起打成单一 `.app`。一个剧作 / 美术不再装六七个工具：装 IDE 就齐。

仓库：[cdotlock/moonshort-ide](https://github.com/cdotlock/moonshort-ide)（私有 — 仓库里**自带一份 live model gateway key**，不要 fork 出去）。  
本机路径：`/Users/Clock/moonshort/moonshort-ide`  
版本：`0.2.0`；`pnpm check` 是绿色门（lint + typecheck + 294 Node test + Go test）

## 两条交互表面

1. **Tab 补全** — 由 `mss-lsp`（Go LSP）+ TextMate grammar 驱动，纯静态分析，无 LLM
2. **Moonshort Agent** — fork 的 Cline 装进 IDE 内，agent-adapter 把 chat-completions 翻成 codex Responses API，跑 `codex 0.130` 二进制（vendored）+ 各 agent 自带的 SKILL.md / CLI bindings

为什么不直接用 VS Code 原生 chat？被 Copilot 闸住 — 详见 [[concepts/moonshort-ide-ai-integration]]。

## 仓库结构

| Path | 是什么 |
|---|---|
| `packages/` | **8 个 bundled extensions**：`mss-lang` / `mss-studio` / `mss-preview` / `mss-workbench` / `mss-welcome` / `mss-workshop` + 共享 `shared` + `agent-adapter` |
| `agents/` | **agent canonical config root** — 每个 agent 一个文件夹（`agent.json` + `skills/` + `cli/bindings.json` + `knowledge/`），由 `fork/build.mjs` 全 bundle 进 `.app` |
| `vendor/` | 内置 `moonshort-script/`（mss + mss-lsp 源）+ `videoctl/` Go 源 + `assetctl/`（assetctl Go binary 全套）+ `vendor-codex/<triple>/codex/codex` 平台二进制 |
| `lsp-server/` | `mss-lsp` Go LSP（其实代码也复用 vendor/moonshort-script/ 内的） |
| `fork/` | VS Code fork build pipeline：`build.mjs` + patches + branding + 重新打 Cline VSIX 的 `build-cline.mjs` |
| `docs/` | `design/`（48 个 spec 含 workshop console / assetctl wave 1-13 / comfyui modal / asset-renderer v10 / production manifest）+ `guides/lsp-upstream.md` |
| `test/`, `tools/` | Node test suite + e2e 验证脚本（含 `verify-codex-host.mjs` / `verify-codex-assetctl.mjs` / `verify-l2-smoke.mjs` 等 L1/L2 验证脚本） |

## Packages（8 个）

| Package | 职责 |
|---|---|
| `mss-lang` | MSS TextMate grammar + LSP client（连本机 `mss-lsp` binary），暴露 `mss` 编译器路径 + `mss-lsp` 路径配置 |
| `mss-studio` | F Studio — 结构化 block-based MSS 编辑器；旁边可切回经典 text editor；asset chips / asset reveal 集成 |
| `mss-preview` | **Preview & Publish** — 播编译产物 + voice casting workbench + **production manifest publish**（走 [[concepts/production-pipeline-two-phase]] 的 submit endpoint）；可配 backend admin URL + `noval_admin` cookie |
| `mss-workbench` | 主交互 surface — Agent Adapter（chat-completions ↔ codex Responses API 桥）+ 各 mode 注入；可配 provider id + OpenAI-compatible base URL（不填走 build-baked 默认 gateway） |
| `mss-welcome` | 欢迎页 + 设置 Moonshort Claude Gateway（Anthropic-compatible base URL）+ auth token |
| `mss-workshop` | **Production Workshop** — Phase 2 Tab 2，跑 agents 流水线；onboarding spotlight tour 状态机 + per-book / per-agent onboarding 持久化 + readiness 检查；minigame workbench + minigame playtest overlay |
| `shared` | 跨 extension 共用类型 + 工具 |
| `agent-adapter` | **codex-shim** HTTP bridge：把 chat-completions 翻成 codex Responses API；reasoning_content round-trip（多 turn thinking-mode agentic）+ trailing-comma JSON 容错 + `CODEX_SHIM_DEBUG` dump 诊断；详见 [[concepts/codex-runtime-and-verification-layers]] |

**Platform rule**：lint 强制 `import "vscode"` 只许从某 package 的 `src/platform-adapter.ts` 进，保证其他文件可单测 / 跨 host。

## Agents（6 个）

`agents/agent.schema.json` 是每个 `agent.json` 的 JSON Schema 校验源。Workshop 是 generic engine，**完全靠这些 manifest 驱动** — 它没有任何"backgrounds" / "characters" / "adaptation" 的硬编码。

| Agent | inputType | assetType | 职责 |
|---|---|---|---|
| `adaptation` | `novel` | — | novel → multi-episode MSS（含 character bible / route plan / wardrobe state checker / final mss pipeline 标准化） |
| `asset` | `mss` | image / video | MSS → 图 / 视频资产（assetctl 后端：背景 / 角色立绘 / CG / cutout / green-spill / hole-fill / matting / upscale 等，详见 [[concepts/assetctl-integration-contract]]） |
| `audio` | `mss` | bgm / sfx | MSS → BGM / sfx 资产（[[concepts/sfx-pipeline]]） |
| `minigame` | `mss` | minigame | MSS → minigame 包（深层 layer 生成：UI / asset / runtime；接 `minigamectl` CLI） |
| `script` | — | — | **hidden** agent — backs IDE Script mode |
| `_shared` | — | — | 不是 agent，是跨 agent 共享材料根（`knowledge/MSS-SPEC.md` + 共享 user/project memory） |

每个 agent 文件夹长这样：

```
agents/<id>/
  agent.json            manifest (ordered stages, gates, asset type)
  skills/<skill>/
    SKILL.md
    references/         self-contained domain docs
    <companion scripts>
  cli/
    bindings.json       declared CLI bindings
    videoctl/           per-CLI 子文件夹
  knowledge/            agent-only知识库
```

## 2026-05 关键改动

### Voice Casting Workbench（[[concepts/production-pipeline-two-phase]] IDE 配套）

进 production manifest 之前必须给每个角色定声音 —— preview 这部分新建：

- **bible voice anchors 抽取**（`4d7a088`）— 从角色 bible 行扫 voice 描述锚点
- **catalog voice pool selection**（`3b62f4b`）+ **profile refinement**（`dab54a6`）+ **auto-assign for ordinary catalog voices**（`5282fb5` model-driven `8631d9e`）
- **voice auditions caching**（`d68f40a`）+ **supporting cast 自动 casting**（`5ff86b3`, `3c4df5a` 测试覆盖）
- **publish gate**：**character voices 必须 fully cast 才允许 publish**（`952fb06`）
- **submit publish 改两阶段**：`a4a9590 feat(preview): publish production manifests` + `a80188c feat(preview): surface two-phase "pending admin review" on publish` + `7e9a602 fix(preview): drop draft-asset pre-registration from publish`
- 老 PATCH voice 直接路径全停（`1e85616 fix(preview): stop syncing voice through direct routes on publish`、`7d4ecab fix(preview): fold voice sync into publish`）

### Workshop Onboarding Spotlight Tour（`codex/workshop-onboarding-guided-tour`）

写作 + 资产生产首次进 workshop 给的引导：

- **onboarding store state machine**（`fbee6b9`）+ readiness 检查链（`5489af2` / `1e4fb6e` / `f1a658b` wire types）
- **per-book persistence**（`46f5476`）+ **memory writes 校验**（`2383595`）+ **auto-start 限 novel workbench**（`2b8de72`）+ **lifecycle 稳定**（`ed54e62`）
- **spotlight tour overlay**（`a7cd7bb`）+ readiness 表面化 / replay（`5eb4745`）+ replay-safe full details（`a18d88f`）
- **per-agent 定制**（`cf64cfd`）+ memory scoped by agent profile（`7c26a92`）
- **复制本地化**：zh suppression copy update（`81e8e66`），onboarding 前置 step 澄清（`51d2583`）

### Minigame Workbench（新）

- `b487b1f feat(workshop): add minigame workbench`
- `1079abd feat(workshop): add minigame playtest overlay`
- `8d49fd2 feat(minigame): surface generation metadata`
- `7d6dc02 feat(minigamectl): list templates`
- **deep minigame layer generation**（`6f52bd2 feat(minigame): expose assetctl to agent` + `6a9135d feat(workshop): prompt deep minigame layers` + `1502999 feat(studio): expose deep minigame layers` + `aebf5d3 feat(studio): pass minigame customization layer`）
- minigame iframe 步 + settlements gating（`d0d1f0c` / `2d15980` / `1c1b57e fix(workshop): open minigames externally from local file` / `34c5fe5 fix(workshop): render minigame playtest from html body`）

### Asset Renderer V10 + Adaptation 强化

- `2026-05-22-asset-renderer-v10-migration-design.md` — 单文件 spec，asset-matting-hybrid 过期、走全链 V10
- `2b3bf6b feat(adaptation): require wardrobe state markers`
- `f8e4527 feat(adaptation): add wardrobe state checker`
- `a73dab2 fix(adaptation): standardize final mss pipeline`
- `efdfeb4 fix(assetctl): rewrite final episode markdown aliases`
- `586f675 Load production prompts from Langfuse`
- `4189372 fix(mobai): route generation through router api` — 全路 mob-ai gateway
- `f5d4eaa fix(assetctl): use async MobAI GPT image generation`

### assetctl Wave 1-13 Foundation（大块工作）

详见独立 concept：[[concepts/assetctl-integration-contract]] / [[concepts/assetctl-skills-sync-and-staging]] / [[concepts/codex-runtime-and-verification-layers]]。简而言之：

- 18 颗 atomic tools（13 runnable + 5 backend FC gateway）
- 2026-05 跨 13 个 wave 推进 F→E/B/E2 pattern 升级
- Langfuse skill overlay + IDE-host TTL cache + 静默回退本地 git
- codex-shim reasoning round-trip + tool L0/L1a/L1b/L2/L2b/L2c 完整验证链

## Toolchain（构建）

| Tool | Version | 用途 |
|---|---|---|
| Xcode Command Line Tools | latest | native module builds (macOS) |
| Node | **≥ 22.18**（`.nvmrc` 钉 22.22.1） | VS Code 1.119.1 build 用 |
| pnpm | 10+ | repo 包管理器 |
| Python | 3.8+ | node-gyp |
| Go | 1.23+ | builds `mss-lsp`, `mss`, `videoctl`, `assetctl` |
| Rosetta 2 | — | **只**用来重新打 Cline（cline bundles x86 `protoc`） |
| zig（CGO 跨编） | — | assetctl Wave 5 后含 cgo（chai2010/webp），linux/windows 跨编需要 |

## 构建

```sh
git clone https://github.com/cdotlock/moonshort-ide.git
cd moonshort-ide
pnpm install
pnpm check                      # 验证门
node fork/build.mjs --platform macos   # → "Moonshort IDE.app"
```

`fork/build.mjs` 期间会下载 Electron / ripgrep / native-module prebuilds + 钉版 `@openai/codex` + `videoctl` Go 模块依赖。代理：先 `export https_proxy=...`。

## 关键 Env / 配置

`mss-preview`（Preview & Publish）：
- `mssPreview.backendAdminBaseUrl` — moonshort-backend admin base URL
- `mssPreview.backendAdminCookie` — 本机 `noval_admin` cookie value/header

`mss-workbench`：
- `mssWorkbench.agentAdapter.provider` — Agent Adapter provider id（e.g. `deepseek`）
- `mssWorkbench.agentAdapter.baseUrl` — OpenAI-compatible base URL（不填走 build-baked default gateway，`.app` 自带 working gateway）

`mss-welcome`：
- `mssWelcome.claudeGateway.baseUrl` — Anthropic-compatible base URL
- `mssWelcome.claudeGateway.token` — auth token

## L2 验证链（codex + agent agentic 真跑）

详见 [[concepts/codex-runtime-and-verification-layers]]。当前可一键 smoke：

| 层 | 脚本 | 状态 |
|---|---|---|
| L0 | `pnpm test` | ✅ 197/197 |
| L1a | `node tools/verify-skill-discovery.mjs` | ✅ 15 asset skills 全发现 + 暴露 |
| L1b | Langfuse overlay 字节落地 | ✅ |
| L2 | `node tools/verify-l2-smoke.mjs` | ✅ mob-ai → codex 0.130 → codex-shim → ChatBackend + CodexBackend 双段返 "PONG" |
| L2b | `node tools/verify-workshop-agent.mjs` | ✅ workshop EXECUTE stage 跑通 + applyPromptMap 写回 |
| L2b-deeper | `node tools/verify-codex-host.mjs` | ✅ claude-sonnet-4-6 真 agentic + multi-turn shell tool |
| L2c | `node tools/verify-codex-assetctl.mjs` | ✅ codex shell → assetctl real-run，env 永久落 `.env` |

## 相关

- [[concepts/moonshort-ide-ai-integration]] — 为什么 fork VS Code + 用 Cline 而不是原生 chat 的架构决策
- [[concepts/codex-runtime-and-verification-layers]] — codex 起飞 + auth 传递 + L0-L2c 验证矩阵
- [[concepts/assetctl-integration-contract]] — asset agent 后端调的 18 颗 atomic tools 契约
- [[concepts/assetctl-skills-sync-and-staging]] — assetctl skills 加载链路（Langfuse + TTL cache + git 回退）
- [[concepts/production-pipeline-two-phase]] — IDE submit 端的后端契约
- [[concepts/comfyui-modal-deploy]] — `matting` / `upscale-image` 走 Modal serverless
- [[entities/moonshort-script]] — 编辑的 MSS 格式 + Go 编译器
- [[entities/moonshort-backend]] — submit 目标 / publish 接收方
- [[entities/assets-produce]] — 上游 novel-to-MSS / 资产渲染参考（IDE 把它的能力内化进 `agents/asset/`）
- [[entities/mob-ai-router]] — Agent / assetctl 调 LLM / image / video 走的 gateway
