# Lunaverse 改名勘察报告（原始证据）

> 勘察日期：2026-06-06
> 勘察范围：`/Users/Clock/lunaverse/` 工作区下全部 13 个顶层目录（9 个独立 git 仓库 + 4 个非 git 目录）
> 目的：为 "lunaverse → Lunaverse"、"LS → Lunascripts / .ls" 的全量改名提供事实底座。
> 本文件已随 Lunaverse 改名同步更新，迁移方案见 `wiki/syntheses/lunaverse-rename-migration.md`。

## 0. 名词确认

- **LS = "Lunascripts"**（在 `lunascripts/README.md:3`、`lunaverse-ide/packages/ls-lang/package.json:21` 的 aliases、`backend/.../skills/ls-syntax/SKILL.md` 均有据可查）。
- 目标命名：项目/平台 **Lunaverse**；脚本语言/格式 **Lunascripts**；缩写 **LS**；文件扩展名 **.ls**。

## 1. 占用量分布（排除 node_modules/.git/dist/build/__pycache__/vendor/.venv 等）

| 目录 | 是否 git 仓库 | `lunaverse`(忽略大小写) | `ls` (词) | `.ls`(扩展引用) |
|---|---|---:|---:|---:|
| lunaverse-ide | ✓ | 1779 | 2834 | 365 |
| backend | ✓ | 947 | 2156 | 151 |
| dramatizer-ls | ✓ | 983 | 593 | 56 |
| lunascripts | ✓ | 109 | 180 | 3 |
| mobai-agent | ✓ | 55 | 0 | 0 |
| lunaverse-cocos-client | ✓ | 24 | 0 | 0 |
| mob-mini-agent | ✓ | 18 | 1 | 0 |
| assets-produce | ✓ | 13 | 0 | 0 |
| demo-example | ✗ | 7 | 0 | 0 |
| wiki（项目内本地目录） | ✗ | 7 | 16 | 0 |
| docs | ✗ | 5 | 0 | 0 |
| dramatizer | ✓ | 3 | 0 | 0 |
| db | ✗ | 0 | 0 | 0 |
| **合计（约）** | | **~3950** | **~5780** | **~575** |

总量约 **1 万处**字符串占用，外加约 **575 个 `.ls` / `.ls.md` 数据文件需要物理改名**。三大重灾区：lunaverse-ide、backend、dramatizer-ls。

## 2. 关键结论：文件扩展名现状是「三套并存」（最易踩坑）

直接核验代码，今天的脚本文件扩展名**并不统一**，存在三种约定：

1. **`.ls`** —— 只有 **IDE** 把它当一等扩展名。
   - `lunaverse-ide/packages/ls-lang/package.json`：语言 `id: "ls"`、`extensions: [".ls"]`、`aliases: ["Lunascripts","LS"]`、grammar `scopeName: "source.ls"`、`activationEvents: ["onLanguage:ls","workspaceContains:**/*.ls"]`。
   - 配套真 TextMate 语法 `syntaxes/ls.tmLanguage.json`，测试 fixture（`test/fixtures/ls-scan/*.ls` 等）也是 `.ls`。
2. **`.md`** —— **真正的编译器只认 `.md`**。
   - `lunascripts/cmd/ls/main.go:243`：`if !strings.HasSuffix(path, ".md")` 才报错——只接受 `.md`。
   - dramatizer-ls 的创作脚本是纯 `.md`（`scripts/` 下 336 个 `.md`）；`lunascripts/testdata` 13 个 `.md`。
   - `LS-SPEC.md` 明确说明刻意选 `.md` 而非自定义后缀（GitHub 可直接预览、无需自定义编辑器）。
3. **`.ls.md`** —— **decompiler 产出**并且是 **backend 生产内容的实际后缀**。
   - `lunascripts/internal/decompiler/decompiler.go:132,140`：硬编码输出 `".ls.md"`，冲突时 `_N.ls.md`。
   - `lunascripts/api_server.py:190`：`fname.endswith(".md") or fname.endswith(".ls.md")` 两者都收。
   - backend：`lunascripts/` 下 **263 个 `.ls.md`**、0 个纯 `.ls`、6 个纯 `.md`。

**含义**：切到 `.ls` 不是简单替换后缀字符串，而是要**统一三套约定**。任何一处漏改都会静默：编译器扫不到文件、IDE 语法高亮失效、decompiler 产出错后缀。`.md` 被刻意选用的「GitHub 可预览」收益会丢失（见方案里的权衡）。

## 3. `lunascripts/` 内容根目录

`lunascripts/` 是脚本内容根目录名（"moon"+"scripts"，源自 Lunaverse），出现在：
- `backend/lunascripts/`
- `dramatizer-ls/lunascripts/` 和 `dramatizer-ls/_deprecated_2026-05-07_render-pipeline-b/lunascripts/`
- 同时是 OSS 路径段与大量文档引用里的前缀。

Lunascripts 之下自然变为 `lunascripts/`，但它牵涉 OSS 路径、README、glob，属结构性改名。

## 4. 七桶分类——各仓库高风险项（buckets 3–7 为非 find-replace 项）

下列为「不能简单全局替换」的项，按仓库与桶罗列。桶 1（品牌/UI/文档）、桶 2（代码标识符）数量大但机械，不在此逐条展开。

### 4.1 lunaverse-ide（VS Code fork，IDE 本体）

**桶 4 App/包身份（高危，外部/持久）** —— `fork/config/product.overrides.json` 整面：
- `nameShort/nameLong: "Lunaverse IDE"`，`applicationName: "lunaverse-ide"`
- `dataFolderName: ".lunaverse-ide"`、`serverDataFolderName: ".lunaverse-ide-server"`（**用户数据目录**，naive 改名会孤立既有设置/状态）
- `win32MutexName: "lunaverseide"`（**改了会让多开实例并存 → 数据损坏**）
- `win32AppUserModelId: "Lunaverse.LunaverseIDE"`、`win32RegValueName/DirName/...`、4 个 Windows MSI GUID
- `darwinBundleIdentifier: "com.lunaverse.ide"`（**macOS bundle id**，改了 = 新 app，孤立旧数据 + 断自动更新 + 断文件关联）
- `urlProtocol: "lunaverse-ide"`（**自定义 URL scheme / 深链**）
- `linuxIconName: "lunaverse-ide"`
- npm 包名：根 `package.json name: "lunaverse-ide"`；`@lunaverse-ide/shared`、`@lunaverse-ide/agent-adapter`；6 个扩展包 `ls-lang/ls-preview/ls-workbench/ls-studio/ls-welcome/ls-workshop`，全部 `publisher: "lunaverse"`。
- 安装产物：`/Applications/Lunaverse IDE.app`，内部扩展目录 `lunaverse-ls-workshop`（见仓库 CLAUDE.md 的 dev-reload 路径）。

**桶 3 扩展名/语言注册（高危）**：
- `packages/ls-lang/package.json`：语言 id `ls`、`.ls`、`source.ls`（见 §2）。
- `packages/ls-studio/package.json`：`filenamePattern: "*.ls"`。
- `syntaxes/ls.tmLanguage.json`：所有 scope 名 `*.ls`（`comment.line.double-slash.ls` 等）。
- LSP：`lsp-server/internal/lsp/server.go` 用 `LS_PATH` 找 `ls` 二进制、`Source: "ls"` 诊断源。
- 测试 fixture 与 test-data 真 `.ls` 文件需物理改名。

**桶 5 持久化/配置（高危，用户设置迁移）**：VS Code 配置键 `lunaverse.lsPath`、`lunaverse.lspPath`、`lunaverse.agent.{apiKey,baseUrl,model,provider,codexPath}`、`lunaverse.authToken`、`lunaverse.gatewayBaseUrl`、`lunaverse.preview.*`、`lunaverse.inlineCompletion.enabled`；环境变量 `LS_PATH`、`LUNAVERSE_AGENT_*`、`LUNAVERSE_BAKED_*`、`LUNAVERSE_SKILL_LANGFUSE_*`、`LUNAVERSE_SCRIPT_DIR`。

**桶 6 外部耦合（高危）**：默认 gateway `https://gateway.lunaverse.com/v1`（`packages/shared/src/types.ts` `DEFAULT_GATEWAY_BASE_URL`）；URL scheme `lunaverse-ide`；Go module `github.com/cdotlock/lunaverse-ide/minigamectl` + `lsp-server/go.mod` 对 sibling `lunascripts` 的本地 replace（路径变了 build 即挂）。

**桶 7 仓库/目录名**：repo 目录 `lunaverse-ide`；6 个 `packages/ls-*`；`test/fixtures/ls-scan`、`ls-scan-dup`；`agents/asset/skills/shot-image-from-ls`。

### 4.2 backend（Next.js 游戏引擎 + admin，品牌内含 "Noval"）

注意：backend 自带品牌 **"Noval"**（`app/layout.tsx` `title: "Noval — Lunaverse"`、DB `noval_demo`、CLI `noval`、容器 `noval-*-dev`）。"Noval" 与 "Lunaverse" 是**两个品牌**，本次只确认改 "Lunaverse"；"Noval" 是否一并改属待拍板项。

**桶 3 扩展名/内容（高危）**：`lunascripts/` 下 **263 个 `.ls.md`** 需物理改名；OSS 路径模板 `episodes/${contentHash}.ls`（checkpoint route）；`docs/ls-refactor/LS-SPEC.md`、`JSON-OUTPUT.md` 权威规范；dream-agent 技能示例 `skills/ls-syntax/examples/full-syntax.ls`。

**桶 7 目录名（高危，技能加载靠目录名）**：dream-agent 5 个技能目录 `ls-syntax`、`ls-syntax-full`、`ls-step-types`、`ls-asset-rules`、`ls-error-recovery`；文档目录 `docs/ls-refactor/`、`docs/ls-refactor-archived/`、`docs/ls-testdata/`、`public/ls-demo/`。技能名同时硬编码在：Langfuse 命名 `dream_agent__skill__ls-syntax`、测试断言（`manager.test.ts`、`validation.test.ts` 期望 `"ls-syntax"`/`"ls-asset-rules"`）。

**桶 5 持久化（高危，需 DB 迁移）**：Prisma `Episode.lsUrl`、`lsAssetId`；JSON 配置/会话键 `lsKey`（`app/lib/attribute-slots.ts`、`save-service.ts` 写进存档 JSON——naive 改会让旧存档读不出）；环境变量 `LS_API_BASE_URL`（指向 `https://lunascripts-production.up.railway.app`）、`LS_API_TIMEOUT_MS`、`R2_BUCKET=lunaverse`、`POSTGRES_DB=noval_demo`。

**桶 6 外部耦合（高危）**：API 路由 `/api/internal/compile-ls`、`/api/internal/decompile-ls`（dream-agent / admin 调用方需同步）；允许登录来源 `https://app.lunaverse.ai`；上游 `lunascripts` Railway 服务 URL；GitHub mirror `github.com/cdotlock/lunascripts`。

### 4.3 lunascripts（LS 语言：Go 编译器/decompiler + FastAPI 包装）

这是 **LS 语言的权威实现**：Go 写的 `ls` 二进制（编译 `.md` → 播放器 JSON、decompile、validate、fix），外加 `api_server.py` FastAPI 包装，部署在 Railway。

- **桶 3（最重要）**：见 §2——`cmd/ls/main.go:243` 只认 `.md`；`decompiler.go:132,140` 输出 `.ls.md`；`api_server.py:190` 收 `.md`/`.ls.md`；testdata 13 个 `.md`。`LS-SPEC.md` 是语言规范。
- **桶 4**：Go module `github.com/cdotlock/lunascripts`（**改了所有 import + 所有 vendored 副本都要改**）；CLI 二进制名 `ls`；FastAPI 标题 "Lunascripts API"。
- **桶 5**：临时目录前缀 `ls_compile_`/`ls_compiledir_`/`ls_decompile_`/`ls_validate_`/`ls_fix_`；二进制路径 `bin/ls`。
- **桶 6**：`lunascripts-production.up.railway.app`；Railway 命令 `railway up --service lunascripts`；OSS 测试路径段 `/lunascripts/testdata/`（baked 进 50+ 快照 JSON——改了快照测试会挂）；Go module path。
- **桶 7**：repo 目录 `lunascripts`。

### 4.4 dramatizer-ls（小说→Lunascripts 生产管线，Python + Skills）

LS 语言的**消费方**：编排小说→脚本，调用 `ls` 二进制编译。仓库名 `-ls` 后缀。
- **桶 3**：创作脚本是纯 `.md`（`compile_ls.py:78` `glob("*.md")`）；2 个 `.ls.md`；技能文档大量 "novel → `.ls`" 表述。
- **桶 2**：`dramatizer/pipeline/compile_ls.py`、`compile_episode()`、`scan_ls()`、`ls_text`/`ls_path` 变量、entity-rename 的 `"ls_token"` 替换类型。
- **桶 6/7**：repo 目录 `dramatizer-ls`；跨仓引用 `cdotlock/lunascripts`、`cdotlock/assets-produce`、`lunaverse-backend`；CLAUDE.md 内非正式称 "Moonscript"。

### 4.5 lunaverse-cocos-client（游戏前端，Cocos Creator；目录名含空格）

**最高危的外部身份集中地**：
- **桶 4（外部不可变）**：Firebase 项目 `lunaverse-1`（`google-services.json:4` ×2）、storage bucket `lunaverse-1.firebasestorage.app`（×4）、auth domain `lunaverse-1.firebaseapp.com`；**Android bundle id `com.mobai.lunaverse`**（`google-services.json:12` ×2，改了断签名/Play 商店身份）；Cocos 项目名 `lunaverse`（`package.json`、`.creator/`）。
- **桶 5**：localStorage 前缀 `STORAGE_PREFIX = 'lunaverse_'`（`assets/core/AppSession.ts:13`，存鉴权 token/用户数据——改了旧会话孤立）。
- **桶 7**：目录名 **`lunaverse-cocos-client` 含空格 + lunaverse**（脚本/CI 里未加引号的路径会脆断；改名顺手把空格也去掉）。

### 4.6 其余轻量目录

- **mobai-agent**：32 处 lunaverse，主要在 skills/memory/架构文档；技能名 `lunaverse-orchestrator`、`lunaverse-game-client`；实体页描述 "Lunaverse platform"。无代码 wiring。
- **mob-mini-agent**：npm 包名 `@lunaverse/mob-agent-foundation`（`pi/packages/foundation/package.json:2`，published/workspace 引用）。
- **assets-produce / demo-example**：OSS bucket `lunaverse-resource`（`demo-example/assets/generate_*.py` 多处硬编码）、DB 名 `lunaverse`（`generate_all.py`）、硬编码路径 `~/lunaverse/assets-produce/.env.example`（opencode 测试）。
- **docs**：~6900 行架构/设计文档引用 "Lunaverse 平台"，需上下文更新，无 wiring。
- **db**：仅一个二进制 `wiki.db`，无文本占用。
- **wiki（项目内本地目录）**：16 处 LS 集中在 `syntheses/minigame-trick-redesign-2026-05.md`（标签、标题、`[[concepts/ls-format]]` 等交叉引用）。

## 5. 不受改名影响（务必不要误改）

- **LS 指令词汇本身**：`@episode`、`@choice`、`@gate`、`@signal`、`@affection`、`@butterfly`、`@cg`、`@minigame` 等是**语言语义 token，不是品牌名**，保持不变。改了会破坏所有现存脚本与编译器。
- 外部第三方包名、上游 VS Code（`github.com/microsoft/vscode`）、GUID 内偶发的 "ls" 子串等。

## 6. 子串误伤风险（naive sed 黑名单）

- `lunascripts`（含 "lunaverse" 邻近语义但要整体改成 `lunascripts`，不是把 "lunaverse" 抠出来）。
- `ls` 作为子串出现在英文单词/URL/GUID 中（用词边界 `\bls\b` 与 `\.ls` 限定）。
- 编译产物 / 快照 JSON（`compiled.json`、含 OSS 路径的测试快照）——改了快照测试挂；应随重新生成而变，不手改。
- 必排目录：`node_modules`、`.git`、`dist`、`build`、`.next`、`out`、`__pycache__`、`.venv`、`vendor`、lockfiles、`*.map`。
