---
title: Lunaverse IDE
tags: [ide, vscode-fork, ls, cline, codex, assetctl, voice-casting, minigame]
sources: []
created: 2026-05-30
updated: 2026-06-16
---

Lunaverse IDE 是给 [[entities/lunascripts]] 编剧 + 资产生产人员用的桌面应用 —— **VS Code 1.119.1 fork** 一层壳，把 LS 编辑、`ls-lsp` 语言服务、`ls` 编译器、`videoctl` / `assetctl` 资产 CLI、Lunaverse Agent（fork 自 Cline）+ codex agent 跑时、以及 Production Workshop 流水线一起打成单一 `.app`。一个剧作 / 美术不再装六七个工具：装 IDE 就齐。

仓库：[cdotlock/lunaverse-ide](https://github.com/cdotlock/lunaverse-ide)（私有 — 仓库里**自带一份 live model gateway key**，不要 fork 出去）。  
本机路径：`/Users/Clock/lunaverse/lunaverse-ide`  
版本：`0.2.0`；`pnpm check` 是绿色门（lint + typecheck + 294 Node test + Go test）

## 两条交互表面

1. **Tab 补全** — 由 `ls-lsp`（Go LSP）+ TextMate grammar 驱动，纯静态分析，无 LLM
2. **Lunaverse Agent** — fork 的 Cline 装进 IDE 内，agent-adapter 把 chat-completions 翻成 codex Responses API，跑 `codex 0.130` 二进制（vendored）+ 各 agent 自带的 SKILL.md / CLI bindings

为什么不直接用 VS Code 原生 chat？被 Copilot 闸住 — 详见 [[concepts/lunaverse-ide-ai-integration]]。

## 仓库结构

| Path | 是什么 |
|---|---|
| `packages/` | **8 个 bundled extensions**：`ls-lang` / `ls-studio` / `ls-preview` / `ls-workbench` / `ls-welcome` / `ls-workshop` + 共享 `shared` + `agent-adapter` |
| `agents/` | **agent canonical config root** — 每个 agent 一个文件夹（`agent.json` + `skills/` + `cli/bindings.json` + `knowledge/`），由 `fork/build.mjs` 全 bundle 进 `.app` |
| `vendor/` | 内置 `lunascripts/`（ls + ls-lsp 源）+ `videoctl/` Go 源 + `assetctl/`（assetctl Go binary 全套）+ `vendor-codex/<triple>/codex/codex` 平台二进制 |
| `lsp-server/` | `ls-lsp` Go LSP（其实代码也复用 vendor/lunascripts/ 内的） |
| `fork/` | VS Code fork build pipeline：`build.mjs` + patches + branding + 重新打 Cline VSIX 的 `build-cline.mjs` |
| `docs/` | `design/`（48 个 spec 含 workshop console / assetctl wave 1-13 / comfyui modal / asset-renderer v10 / production manifest）+ `guides/lsp-upstream.md` |
| `test/`, `tools/` | Node test suite + e2e 验证脚本（含 `verify-codex-host.mjs` / `verify-codex-assetctl.mjs` / `verify-l2-smoke.mjs` 等 L1/L2 验证脚本） |

## Packages（8 个）

| Package | 职责 |
|---|---|
| `ls-lang` | LS TextMate grammar + LSP client（连本机 `ls-lsp` binary），暴露 `ls` 编译器路径 + `ls-lsp` 路径配置 |
| `ls-studio` | F Studio — 结构化 block-based LS 编辑器；旁边可切回经典 text editor；asset chips / asset reveal 集成 |
| `ls-preview` | **Preview & Publish** — 播编译产物 + voice casting workbench + **production manifest publish**（走 [[concepts/production-pipeline-two-phase]] 的 submit endpoint）；可配 backend admin URL + `noval_admin` cookie |
| `ls-workbench` | 主交互 surface — Agent Adapter（chat-completions ↔ codex Responses API 桥）+ 各 mode 注入；可配 provider id + OpenAI-compatible base URL（不填走 build-baked 默认 gateway） |
| `ls-welcome` | 欢迎页 + 设置 Lunaverse Claude Gateway（Anthropic-compatible base URL）+ auth token |
| `ls-workshop` | **Production Workshop** — Phase 2 Tab 2，跑 agents 流水线；onboarding spotlight tour 状态机 + per-book / per-agent onboarding 持久化 + readiness 检查；minigame workbench + minigame playtest overlay |
| `shared` | 跨 extension 共用类型 + 工具 |
| `agent-adapter` | **codex-shim** HTTP bridge：把 chat-completions 翻成 codex Responses API；reasoning_content round-trip（多 turn thinking-mode agentic）+ trailing-comma JSON 容错 + `CODEX_SHIM_DEBUG` dump 诊断；详见 [[concepts/codex-runtime-and-verification-layers]] |

**Platform rule**：lint 强制 `import "vscode"` 只许从某 package 的 `src/platform-adapter.ts` 进，保证其他文件可单测 / 跨 host。

## Agents（6 个）

`agents/agent.schema.json` 是每个 `agent.json` 的 JSON Schema 校验源。Workshop 是 generic engine，**完全靠这些 manifest 驱动** — 它没有任何"backgrounds" / "characters" / "adaptation" 的硬编码。

| Agent | inputType | assetType | 职责 |
|---|---|---|---|
| `adaptation` | `novel` | — | novel → multi-episode LS（含 character bible / route plan / wardrobe state checker / final ls pipeline 标准化） |
| `asset` | `ls` | image / video | LS → 图 / 视频资产（assetctl 后端：背景 / 角色立绘 / CG / cutout / green-spill / hole-fill / matting / upscale 等，详见 [[concepts/assetctl-integration-contract]]） |
| `audio` | `ls` | bgm / sfx | LS → BGM / sfx 资产（[[concepts/sfx-pipeline]]） |
| `minigame` | `ls` | minigame | LS → minigame 包（深层 layer 生成：UI / asset / runtime；接 `minigamectl` CLI） |
| `script` | — | — | **hidden** agent — backs IDE Script mode |
| `_shared` | — | — | 不是 agent，是跨 agent 共享材料根（`knowledge/LS-SPEC.md` + 共享 user/project memory） |

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
- `a73dab2 fix(adaptation): standardize final ls pipeline`
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

## 2026-06 关键改动

### Unified Login + User Gateway（`codex/unified-login-surface` → `codex/user-auth-gateway-usage`）

IDE 从"各 extension 自带 token"切到统一 login surface + IDE backend gateway 模式：

- **gateway 设计** — `3844247 docs(auth): design gateway user authorization` + `20d2ea7 docs(auth): plan user gateway implementation`
- **共享 auth contract** — `42a1eb7 feat(auth): add shared lunaverse auth contract` + `2f77c22 feat(auth): store ide login tokens in secret storage`
- **全路由走 gateway** — `42c4bc6 feat(auth): route model calls through ide gateway` + `20462c1 feat(auth): route external resources through ide gateway` + `3bd9f17 feat(auth): upload workshop assets through ide backend`
- **agent 统一走 login gateway** — `504dda1 fix(auth): route bundled agents through login gateway` + `027478f fix(agent): route logged-in users through IDE gateway` + `e0aea10 fix(auth): share login token with workshop`
- **upstream login surface 清理** — `e05f739 fix(auth): remove upstream login surfaces` + `249b270 fix(build): scrub deleted auth extensions from VS Code dirs.ts + compile list`
- **invite signup** — `d7bebe9 Add invite signup to IDE login`
- **shell 品牌化** — `871be6c fix(shell): show user initial in account icon` + `430c529 fix(shell): brand accounts entry as Lunaverse` + `f3abe88 fix(shell): hide native account menu actions`

### USD Cost Usage Display

登录用户看到自己的 API 用量（美元计价）：

- `f87170f docs(auth): design USD cost usage display` + `bbfecd4 docs(auth): cover all paid USD cost categories` + `bb2e49c docs(auth): plan USD cost usage implementation`
- `ed9257b feat(auth): display USD cost usage` + `059dcf3 fix(auth): compact usage and hide native AI status`
- `acf9044 feat(auth): show unlimited usage in IDE`

### Welcome Two-Door Entry（新首次体验）

首次打开不再落空白编辑器 —— Welcome page 做成两扇门（编剧 / 资产）：

- `b5bc261 docs: add Welcome two-door entry design spec` + `52b3c9c docs: add Welcome two-door entry implementation plan`
- `d28394a feat(welcome): two-door entry with top gateway bar` + `a32d596 feat(welcome): show welcome on first open of each workspace` + `24f7eb4 fix(welcome): open Welcome on first run instead of a blank editor`
- `b26af2e feat(welcome): activity-bar icon launches Welcome page` + `c6b57a8 feat(welcome): english door copy and centered sign-in modal`
- `ff56fb2 fix(welcome): require a title and use placeholder samples in the first-run form` + `6b64bf1 fix(welcome): open the new episode after Create so the writer isn't stranded`

### Direction A 视觉大改 + Moon Phase Progress

全 IDE 跑一遍 "Direction A" 视觉方向：夜空星空 + 月亮主题：

- **token 基底** — `60b96bb feat(design): Direction A token foundation + shared Moonshort starfield`
- **各 surface 落地** — `dfe92a7 Welcome` / `0183aa4 Workshop console` / `65839d6 Preview stage` / `79fe130 Studio editor` + bold pass（`56eddb9` / `76e6acf` / `e222572`）
- **月亮细节** — `29ddcf5 real var-driven moon` + `6ad2a12 craters/maria + spherical shading` + `78a5c8e Preview + Welcome moonrise` + `cee16be phase the moon per surface`
- **Workshop moon-phase progress** — `4b4080e progress logic` + `081aede drive starfield moon from book progress` + `fd03cfa show moon-phase readout on home` + `26294df project-progress moon measures publish-readiness`
- **Workshop Home 重设计** — `a86a508 feat(workshop): redesign the home into a production dashboard (Direction 2)` + `5da3ce5 clamp home card descriptions`

### Style Studio + style→Langfuse 迁移（6 Wave）

风格系统从静态 JSON 迁到 Langfuse 管理 + IDE 内可增删改查：

- **迁移设计** — `d94ab04 docs: add style→Langfuse migration design (16 families, 6 waves)`
- **W1** `91b3341 seed 16 style families to Langfuse production` → **W2** `4ed828f read style catalog from Langfuse in IDE host` → **W3** `55603b8 host write path — sync/promote gate/versions/archive + R2 upload` → **W4** `67b76f2 full style CRUD UI in the Workshop` → **W5** `ff5d8f0 render pipeline reads styles from Langfuse with local fallback` → **W6** `7ad5ee2 test + fcf7ba1 mark styles.json as emergency fallback`
- **style preview 生成** — `082a468 feat: generate style preview images` + `fb13e52 fix: mirror style previews to r2` + `bc99576 show live style preview generation progress`
- **Style Studio 入口** — `1ba54f1 expose style studio from workshop picker` + `03f2d7f redesign style catalog picker` + `39e3e16 drop the redundant Style Studio node`

### Local-First Custom Styles（Beta）

用户可在 IDE 内本地创建 / 编辑自定义风格（beta quota 限额）：

- `594cc23 docs(design): add local-first custom-styles spec (beta quota + lazy ref upload)`
- `c94f08c feat(workshop): add local-first custom-style store (CRUD + catalog projection)` + `109aefb merge local custom styles into the style catalog`
- `21517c2 custom-style CRUD UI + handlers with beta quota` + `bc99292 host↔webview message protocol`
- `483967d create + edit local custom styles inside the Style Studio flow` + `3b67b40 require all 4 custom-style templates + make the name renameable`
- `fb12348 fix(workshop): reconcile custom styles after a host-rejected save` + `f69cfb6 / 7dced08 eliminate silent inconsistencies`

### Local-First Asset Mapping + Preview

Workshop 产的资产先落本地文件系统，Preview 直接从本地读：

- `5706aad docs(design): add workspace path spec (local-first + existence ground truth)` + `d5efa79 docs(agents): teach production agents the local-first + existence path contract`
- `92334bf feat(workshop): auto-produce a local-first asset mapping for preview` + `8eae70d complete the local mapping by scanning the asset-img library` + `628ee2a write the local mapping in the spec shape lsc reads`
- `b90d6fc fix(preview): render a local, partially-rendered book` + `c5da897 resolve lsc's root-absolute asset bake against the book root`
- `3e830b9 feat(workshop): host-inject local landing paths + existence truth into render manifest`
- `8683557 feat: build workshop asset tree from book root without mapping.json`

### assetctl Look Pipeline（Stage 06 Description Atoms）

sprite 渲染前的 "描述原子" 链 —— 从 bible / LS 自动推导人物 / 场景 / 着装 prompt：

- **build-sprite-tasks** — `04e934e feat(assetctl): add build-sprite-tasks atom` + `ec36068 emits 着装/神态 prompt segments` + `b75b2ba honors wardrobe markers and reserved staging keywords`
- **build-character-prompts** — `7f06aae atom — bible to render-ready character descriptions` + `2b46199 covers supporting cast`
- **build-scene-prompts** — `30079f9 atom — locations + @bg refs to scene descriptions`
- **build-wardrobe-map** — `75ba788 locks outfits to the bible wardrobe table`
- **apply-look-aliases** — `bd7573d emits natural-language sprite prompts`
- **aspect guard** — `67c5e0d verify, retry, center-crop image renders to the expected ratio` + `26357a4 send input.aspectRatio to the router`
- **R2 durable mirror** — `b23836f feat(assetctl): generate-image-gpt can mirror its render to durable R2`
- **WebP 统一** — `da79d0d feat(asset-skills): enforce WebP delivery for bg/CG/cover renders` + `7255935 standardize all image generation on GPT image, drop nanobanana`

### OSS → R2 迁移

上传通道从阿里云 OSS 切到 Cloudflare R2：

- `c029a3c docs: design for OSS→R2 upload migration`
- `a7bde01 refactor(assetctl): replace Aliyun OSS upload with Cloudflare R2` + `c791201 rename oss-put → r2-put in skills, bindings, knowledge`
- `1ec67bc refactor(ide): point the TS upload path at r2-put and R2 env` + `91dc314 refactor(pipeline): use r2-put and forward R2_* env`
- `fdd7327 refactor(modal-comfy): upload to Cloudflare R2 via boto3`

### Adaptation Agent 强化

- **entity-rename** 升为正式 pipeline stage — `60cdb91 migrate entity-rename skill into IDE` + `5d23371 track entity-rename as a pipeline stage` + `a13bcbc make entity-rename a mandatory pipeline step` + `f85e5a3 entity-rename scans .ls/.mss finals`
- **coverage gates** — `04e737c wardrobe + plan-signal coverage gates against silent beat drops` + `d2db63e signal gate treats CRUCIAL as designation` + `2fb5ae4 signal gate honors nickname renames` + `9f123ca check_look_variety gates single-pose supporting cast`
- **MC staging** — `8be99eb feat(adaptation): MC on-stage rule + check_mc_staging hard gate`
- **POV disambiguation** — `86947e9 feat(adaptation): book-aware POV disambiguation with cross-line subject carry`
- **skill 重构** — `8635adc 重构 character-architect 和 bible-reviewer 模板` + `91f4a1e 增强 entity-planner 和 planner-reviewer` + `6765d82 add life-quest scoring` + `226c07b recover arc-reviewer`

### Skills Enforcement

防止 agent 幻觉出不存在的 LS 指令：

- `b77c7fb fix(skills): forbid invented @signal kinds / @option modes, enforce brave-needs-check`
- `0785e8e fix(skills): conform adaptation LS authoring to canonical position-free syntax`

### Workshop Agent 体验改进

- **AGENTS.md manual** — `df4cc4a feat(workshop): load per-agent AGENTS.md manual as codex standing instructions` + `42fa134 retire structured charter in favour of AGENTS.md manuals`
- **Task Plan panel** — `af1e3f8 feat(workshop): surface agent plan.update as a persisted Task Plan panel` + `3df6218 resizable structure-tree / detail / task-plan panels`
- **left-agent handoff** — `21a0a48 feat(workshop): hand adaptation drafts to the left Agent for refinement`
- **quiet runs** — `9261bbf feat(workshop): surface quiet agent runs`
- **resizable panels** — `3fda79d / 3df6218 resizable panels` + `0e8ea31 / aec7034 persist panel sizes`
- `cd4c9a6 fix(workshop): preupload regen image references`

### Preview Player Render Layer（production player 移植）

- `3c58fbb feat(ls-preview): vendor and port the production player render layer` + `3b10730 render PlayerStage via a cursor state machine` + `e80889b thread protagonist slug through the preview payload`
- `350a1aa fix(preview): regenerate player CSS so the stage isn't collapsed to zero height`

### MSS New-Spec 对齐

IDE 内 MSS 模型 + 资产扫描对齐到新版 keyword-free 语法：

- `71bb3ac feat(shared): migrate MSS model + stage compute to the new spec grammar` + `4e413f4 test(mss): update fixtures + tests` + `e4054f8 feat(mss-workshop): scan new keyword-free MSS syntax in asset scanners`
- `37d8564 feat(studio): align card editor + preview stage to the new MSS spec`

### F Studio 编辑器改进

- `c53cde9 feat(studio): delete selected beats with Delete/Backspace` + `30f3ed8 announce editor actions in the status bar via aria-live`
- `1935cc9 feat(a11y): arrow-key caret navigation between beats (roving tabindex)` + `12cc26f raise muted/faint text to WCAG AA contrast`
- `987363a fix(studio): reject retired pose verbs so @char look no longer corrupts a beat` + `647bfa8 toggle IfBlock from the whole header`

### Cloud Asset Pipeline

多剧目云端渲染流水线标准化（`dont-pretend-with-us` Arcane 风格全量渲染跑通）：

- `214df17 feat(asset-pipeline): SLUG-driven run.sh + finalize.py for multi-drama cloud runs` + `18e4199 make style + slug configurable for multi-drama runs`
- `62aa5f0 feat(pipeline): checkpoint render state every 5 min (survive cloud suspend)`
- `2c39380 feat(second-chorus): self-contained cloud-runnable asset pipeline`
- 大量 `dont-pretend-with-us` Arcane render checkpoint（300+ bg / sprite / CG 完成）

### Build & 分发

- **Developer ID 签名 + 公证** — `4a9b176 feat(build): sign + notarize macOS app with Developer ID instead of ad-hoc`（不再 ad-hoc，走正式 Apple 签名）
- **Moonshort → Lunaverse 更名** — `3c55616 chore: rename Moonshort IDE to Lunaverse` + `cc55f4a fix: complete Lunaverse rename test contracts`
- **codex-shim 稳定性** — `db4d28c feat(agent-adapter): absorb transient gateway 5xx in the codex shim` + `84ce1de make the shim gateway retry fail fast` + `c30d956 raise shim stream idle-abort to 180s` + `cb8c1c7 force loopback into NO_PROXY`

## Toolchain（构建）

| Tool | Version | 用途 |
|---|---|---|
| Xcode Command Line Tools | latest | native module builds (macOS) |
| Node | **≥ 22.18**（`.nvmrc` 钉 22.22.1） | VS Code 1.119.1 build 用 |
| pnpm | 10+ | repo 包管理器 |
| Python | 3.8+ | node-gyp |
| Go | 1.23+ | builds `ls-lsp`, `ls`, `videoctl`, `assetctl` |
| Rosetta 2 | — | **只**用来重新打 Cline（cline bundles x86 `protoc`） |
| zig（CGO 跨编） | — | assetctl Wave 5 后含 cgo（chai2010/webp），linux/windows 跨编需要 |

## 构建

```sh
git clone https://github.com/cdotlock/lunaverse-ide.git
cd lunaverse-ide
pnpm install
pnpm check                      # 验证门
node fork/build.mjs --platform macos   # → "Lunaverse IDE.app"
```

`fork/build.mjs` 期间会下载 Electron / ripgrep / native-module prebuilds + 钉版 `@openai/codex` + `videoctl` Go 模块依赖。代理：先 `export https_proxy=...`。

## 关键 Env / 配置

`ls-preview`（Preview & Publish）：
- `lsPreview.backendAdminBaseUrl` — lunaverse-backend admin base URL
- `lsPreview.backendAdminCookie` — 本机 `noval_admin` cookie value/header

`ls-workbench`：
- `lsWorkbench.agentAdapter.provider` — Agent Adapter provider id（e.g. `deepseek`）
- `lsWorkbench.agentAdapter.baseUrl` — OpenAI-compatible base URL（不填走 build-baked default gateway，`.app` 自带 working gateway）

`ls-welcome`：
- `lsWelcome.claudeGateway.baseUrl` — Anthropic-compatible base URL
- `lsWelcome.claudeGateway.token` — auth token

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

- [[concepts/lunaverse-ide-ai-integration]] — 为什么 fork VS Code + 用 Cline 而不是原生 chat 的架构决策
- [[concepts/codex-runtime-and-verification-layers]] — codex 起飞 + auth 传递 + L0-L2c 验证矩阵
- [[concepts/assetctl-integration-contract]] — asset agent 后端调的 18 颗 atomic tools 契约
- [[concepts/assetctl-skills-sync-and-staging]] — assetctl skills 加载链路（Langfuse + TTL cache + git 回退）
- [[concepts/production-pipeline-two-phase]] — IDE submit 端的后端契约
- [[concepts/comfyui-modal-deploy]] — `matting` / `upscale-image` 走 Modal serverless
- [[entities/lunascripts]] — 编辑的 LS 格式 + Go 编译器
- [[entities/lunaverse-backend]] — submit 目标 / publish 接收方
- [[entities/assets-produce]] — 上游 novel-to-LS / 资产渲染参考（IDE 把它的能力内化进 `agents/asset/`）
- [[entities/mob-ai-router]] — Agent / assetctl 调 LLM / image / video 走的 gateway
