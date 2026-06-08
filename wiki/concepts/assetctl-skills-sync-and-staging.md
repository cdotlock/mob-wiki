---
title: assetctl skills sync + Block 2/3 staging（codex skill 加载链路）
created: 2026-05-20
updated: 2026-05-21
tags: [assetctl, block-2, block-3, codex, langfuse, skill-loader, skill-staging, lunaverse-ide]
status: draft
---

# assetctl skills sync + Block 2/3 staging（codex skill 加载链路）

把 codex 内的 skill body **从本地 git 唯一源** 升级为 **Langfuse production label 优先 + 本地 git 兜底**。Block 2 = skill 内容/编排骨架；Block 3 = Langfuse-first loader + IDE wiring。两块在 2026-05-20 一起合 lunaverse-ide main @ `266cd3c`。

> 设计 spec：
> - `lunaverse-ide/docs/design/2026-05-20-block-2-orchestration-skill-spec.md`（472 行）+ `…plan.md`（619 行）
> - `lunaverse-ide/docs/design/2026-05-20-block-3-langfuse-loader-spec.md`（372 行）+ `…plan.md`（438 行）
>
> 关联：[[concepts/assetctl-integration-contract]]（Block 1 原子能力契约）· [[entities/lunaverse-ide]]

## 一句话

stageSkills 在 cp 本地 skill 文件夹之后**再 spawn 一次 `assetctl skills load`** 把每个 SKILL.md 用 Langfuse production label 内容覆盖；Langfuse 不可达任意原因（凭据缺失/网络/5xx/parse 失败/缺二进制）→ 静默回退本地 cp 字节，永不抛错。同一 IDE 进程内 TTL 窗口（默认 60s）跳过重复 spawn。

## Block 2 现状（基本已落地）

| Layer | 状态 | 备注 |
|---|---|---|
| 12 个 asset-generation spec wrap 为 IDE skill | ✅ 完成 | `agents/asset/skills/<spec>/SKILL.md`，frontmatter `name`/`description`/`allowed-tools` 三必填 |
| 3 个 IDE 原创 controller skill | ✅ 完成 | `asset-prompt-generator`/`asset-renderer`/`asset-reviewer` |
| 8 个 novel-to-video refs 落 `asset-prompt-generator/references/` | ✅ 完成 | character-reference-policy, director-playbook-core, langfuse-draft, shot-id-policy, video-prompt-standard 等 |
| 3 个 novel-to-video refs 落 `asset-renderer/references/` | ✅ 完成 | seedance-core-lessons, video-prompt-standard, videoctl-tool-reference |
| `style-prompts/` 同步 | ✅ 设计上不同步 | codex 通过 `mcp__style-prompts__*` MCP 动态查（spec §D3 决策）；`agents/_shared/knowledge/nrbi-styles.json` 是 IDE 自维护 fork |
| `_shared/knowledge/` cross-refs（4 个 NRBI skill body） | ✅ 完成（本次） | DOC-1 fix `3261365`：4 个 SKILL.md body 加 References 段，repo-absolute path `agents/_shared/knowledge/nrbi-{pipeline-manifest.md,styles.json}` |
| `shot-image-from-ls` frontmatter ⊇ body 工具集 | ✅ 完成（本次） | B2-15 fix `b9a5f8f`：补全 `generate-video-happyhorse, crop-video` 两颗 fallback 工具授权 |
| `agents/asset/skills/README.md` 导航 | ✅ 完成（本次） | B2-14 `b54e229`：83 行导航 doc，kind→skill 表 + 3 controller + cross-refs + reading order；无 frontmatter、无 emoji、无 Co-Authored-By |
| Block 2 smoke test（15 skills stage + parse） | ✅ 完成（本次） | B2-16 `4a68924`：`test/workshop-codex-home.test.mjs` 加 "Block 2 smoke" 测，15 skill 全部 stage + frontmatter 三必填断言通过 |
| 跨 skill audit（frontmatter ⊆ legit / == body / Block-1 coupling） | ✅ 通过 | B2-15 audit：15 skills 全 GO，0 CRITICAL / 0 WARNING（fix 后）/ 3 NOTE（3 controller 无 "Atomic tools" body 段，是 controller 范式，frontmatter 唯一真相） |

**不做**（D 决策已划掉）：
- 移 `sfx-spec`/`music-spec` 到 `agents/audio/skills/`（R1）—— TBD lock 留在 asset/，除非 reviewer 改主意
- frontmatter `version` 字段强制要求 —— TBD lock 拒绝
- 实现 spec §6 row #17/#18（ATOMIC_TOOL_IDS / SKILL_PICK_PROMPT）—— Block 1 有 ID 表，codex 不需要 picker prompt

## Block 3 现状（双层都完成）

### Go 层（fleet 2026-05-20 提前完成）

| 包 | commit | 备注 |
|---|---|---|
| `internal/skills/langfuse` | B3-2 `6fedacc` | net/http client 映射 Langfuse v2 API（GET `/api/public/v2/prompts/{name}`、POST `/api/public/v2/prompts`），Basic Auth `publicKey:secretKey`，进程内 TTL 缓存（key = `(name, label)`），CallError 区分 401/403/402/429-quota（INVALID_INPUT）vs 429-rate/5xx（TRANSIENT），覆盖 91.1% |
| `internal/skills/loader` | B3-3 `0af7e0b` | `(*Loader).Load(ctx, name, label) ([]byte, source, error)`：Langfuse 优先 → 任何失败（5xx/网络/timeout/404/auth/空体/无效 frontmatter）静默回退本地 git；落地顺序 `agents/_shared/skills/<name>/SKILL.md` → `agents/<id>/skills/<name>/SKILL.md`；本地兜底结果也被 TTL 缓存（spec §5.5 row 4），覆盖 90.7% |
| `internal/skills/sync` | B3-4 `1fd84e3` | `Sync(opts)` push 方向 ＋ parity（`--check`）+ dry-run；最佳努力（单 skill 错误不阻塞）；只在 `--label production` lint；覆盖 90.6% |
| CLI `skills sync` | B3-5 `e820202` | 子命令 + flag 解析 + env 读取（`LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`）+ LUNAVERSE_SKILL_LANGFUSE_TTL_MS；exit code 推导（lint fail=4、drift=6、5xx=5、auth=4）；覆盖 85% |
| Vendor README | B3-6 `a14b5fb` | Block 3 段 pin spec anchor，commit `feb012f` |

### Go 层新增（本次）

`assetctl skills load` 子命令——**read 方向**，是 fleet `skills sync` 的对称镜像。

| 包/文件 | commit | 备注 |
|---|---|---|
| `internal/skills/walk.go`（提取） | `424d514` refactor | `enumerateLocalSkills(localRoot)` 从 `sync.go` 抽出共享，sync + load_writer 都用 |
| `internal/skills/load_writer.go` | `8638719` feat | `LoadAll(ctx, opts)`：遍历 local skill 树 → 每颗 `Loader.LoadDetail(name, label)` → 写 `<dest>/<name>/SKILL.md`；返回 `Report{Results[], Failed[]}` |
| `internal/cli/skills.go` 加 load arm | `bc691c8` feat | `skillsLoadCmd(args, stdout, stderr)`：parse `--label`/`--local-root`/`--dest`/`--name`，build Loader + LoadWriter，单行 envelope `{ok:true, data:{label, results:[{name,label,source,langfuseVersion?}, ...]}}` |
| Vendor README docs | `4962439` docs | `assetctl skills load` 子命令文档段 |
| `--name not found` exit 4 修正 | `4a258ea` fix | spec §B 要求 `--name X` 不存在 → exit 4（INVALID_INPUT），不是 exit 6（INTERNAL）；`allLocalMissing` helper 检测 |
| 双 LocalRoot foot-gun 修正 | `650d681` refactor | 删 `LoadOpts.LocalRoot`，loader 是 LocalRoot 单一真相源 |
| walk callback comment 修正 | `74d8cd5` docs | WalkDir error 语义注释与行为一致 |
| Block 3 env table | `266cd3c` docs | vendor/README 加 IDE deployer env vars 表 |

**Go 层覆盖率**（最终）：`internal/skills` 91.4% · `internal/cli` 89.2% · 其他包未回归。

**CLI 退出码**（`skills load` 冻结合同）：
| exit | 含义 | error.code | retryable |
|---|---|---|---|
| 0 | OK | — | — |
| 2 | usage error | — | — |
| 3 | **不使用** | — | — |
| 4 | invalid input（bad `--label`、缺 `--local-root`/`--dest`、`--name` 不存在） | INVALID_INPUT | false |
| 5 | **不使用**（Langfuse 5xx 静默回退 D1） | — | — |
| 6 | no skills found 或 write IO error | INTERNAL | 视情形 |

注：与 `skills sync` 的差别 = `skills load` **缺凭据不报 exit 3**（视为"Langfuse 不可达"→ 全 results `source:"local"` → exit 0），spec §2.1 D1 静默回退不变式。

### IDE TS 层（本次完成 S1-S4 + cleanup）

| Slice | commit(s) | 备注 |
|---|---|---|
| S1 · Go `skills load` CLI | 见上 Go 层新增段 | 4 + 1 + 2 + 1 = 8 commit |
| S2 · TS stageSkills 集成 | `14af858 feat` + `228b1e5 test` + 4 quality fix | `packages/ls-workshop/src/codex-home.ts` 两阶段流程：cp 本地文件夹 → spawn `assetctl skills load` 覆盖 SKILL.md → 解 envelope 记 `source:langfuse|local` per skill；`runCli` 重用（S2 quality fix 把 NIH `spawnAssetctlLoad` 收掉用 `runCli(binary, args, undefined, 0)`） |
| S3 · LANGFUSE_* 环境注入 | **零代码**（确认 `spawn` 默认继承 `process.env`）+ `266cd3c docs` | vendor/README 加 Block 3 env table |
| S4 · IDE-host TTL cache | `34d960a feat` + `3c1af68 test` + 4 quality fix | 提取 `packages/ls-workshop/src/assetctl-bridge.ts`（349 行）：模块级 `Map<cacheKey, {results, expiresAt}>`，key = `repoRoot:::agentDir:::sharedDir:::label`，TTL per-call 从 env 读（默认 60_000ms）；cache 存 SKILL.md body 字节（不光 envelope metadata）以保 §D byte-identity；失败不缓存（spec §F） |

**IDE 层数据流**（post-S4）：

```
stageCodexHome(agentDir, sharedDir, options) called
  ↓
Pass 1: cp -r agents/<id>/skills/*/  → $CODEX_HOME/skills/*/
  (existing behavior; copies entire skill folder incl. references/, assets/)
  ↓
Pass 2: assetctl skills load
  ↓
  cache.get(key = repoRoot:::agentDir:::sharedDir:::label)
    ├─ cache hit + not expired → applyCachedResults() 覆盖 SKILL.md from cached body → log lines → return
    ├─ cache miss / expired → spawn `assetctl skills load --label X --local-root Y --dest Z`
    │    ├─ exit 0 → parse envelope → read each <dest>/<name>/SKILL.md back → cache.set
    │    └─ exit !0 / missing binary / spawn error / parse fail → log warning, NOT cached, return
  ↓
  per-skill log: "skill <name> loaded from <source>[+v<langfuseVersion>] [(cached)]"
```

**测试覆盖**（TS 侧 `test/workshop-codex-home.test.mjs`）：

| 测试名 | 验证 |
|---|---|
| T1 overlay on success | fake binary 返回 ok envelope → 覆盖后 SKILL.md = Langfuse 字节（非本地 git 字节） |
| T2 non-zero exit fallback | fake binary exit 6 → fall back 本地 cp'd 字节 + warning log |
| T3 ASSETCTL_BINARY missing skip | env 指向不存在路径 + 无 vendored binary → 优雅跳过 + warning log |
| log=undefined default | 默认 `options = {}` → 不抛错 + 行为不变 |
| T-cache-1 hit within TTL | 同一 key 第二次 stage 不再 spawn（计数器 = 1） |
| T-cache-2 expiry past TTL | TTL=1ms + 25ms sleep → 第二次 stage 重新 spawn（计数器 = 2） |
| T-cache-3 key sensitivity | 不同 (agentDir/sharedDir/label/repoRoot) 各自独立缓存 |
| T-cache-empty-results | ok envelope + `results: []` → 第二次 stage 仍 cache hit |
| Block 2 smoke (15 skills) | 实仓 agents/asset/skills/ 15 颗全部 stage + frontmatter 三必填断言通过 |

全量 `pnpm test`：**196/196 PASS** · `pnpm typecheck` clean · `pnpm lint` clean。

## Block 3 IDE 环境变量（IDE deployer 必看）

IDE 主进程（Electron main）必须在启动前/spawn 前 export 这些 env vars。`spawn()` 默认继承 `process.env`，子进程 `assetctl` 自动拿到。

| Var | Required | Purpose |
|-----|----------|---------|
| `LANGFUSE_HOST` | yes（走 Langfuse 路径必填） | e.g. `prompt.mobai-game.com` |
| `LANGFUSE_PUBLIC_KEY` | yes | API public key |
| `LANGFUSE_SECRET_KEY` | yes | API secret key |
| `LUNAVERSE_SKILL_LANGFUSE_LABEL` | no（默认 `"production"`） | 加载哪个 Langfuse label |
| `LUNAVERSE_SKILL_LANGFUSE_TTL_MS` | no（默认 `60000`） | IDE-host cache TTL（毫秒） |
| `ASSETCTL_BINARY` | no（默认 `<repoRoot>/agents/asset/cli/assetctl/bin/assetctl`） | binary 路径覆盖（测试/CI 用） |

任何 LANGFUSE_* 缺失 → `assetctl skills load` 静默回退本地 git body（spec §2.1 D1），envelope 返回 `source:"local"` for all skills，exit 0。

## ✅ B3-IDE-5 Langfuse 首次 bootstrap 完成（2026-05-21）

23 个 SKILL.md（asset 15 + dramatizer 8）已 push 到 Langfuse 自部署实例 `prompt.mobai-game.com` / org `mobai` / project **`Lunaverse-IDE`**（org/project id `cmpe3kntg00kprq07ozupgnsa`，独立于历史 `Dramatizer` project 不污染）。两个 label 各一遍：staging 23/23 created + production 23/23 created。

**Project 取名约定**：`Lunaverse-IDE` 跟 lunaverse-ide 仓库名对齐。以后 IDE 范畴所有 SKILL.md prompts 都装这里；dramatizer Go binary 自家的 `phase2-*`/`phase3_*`/`v2-*` prompts 仍在 `Dramatizer` project 单独维护，互不干涉。

**Prompt 命名约定（确立）**：直接用 skill name as-is，**不加前缀**（如 `cg-render-spec`，不是 `skill_cg-render-spec`）。这跟 assetctl `skills sync` 当前实现一致；以前 assets-produce / opencode 团队 push 到 `Dramatizer` project 的旧 `skill_*` 是历史包袱。

### 最终审计（跑 `assetctl skills load` 链路）

| Label | source:langfuse | 字节匹配本地 SKILL.md |
|---|---|---|
| staging | 23/23 | 23/23 |
| production | 23/23 | 23/23 |

### bootstrap 流程（实际跑通版本）

```bash
# 1. 在 IDE 主仓根目录 export 凭据
export LANGFUSE_HOST=https://prompt.mobai-game.com     # 注意带 scheme
export LANGFUSE_PUBLIC_KEY=pk-lf-...                   # Lunaverse-IDE project 的 keypair
export LANGFUSE_SECRET_KEY=sk-lf-...

# 2. push staging（不 lint）
./agents/asset/cli/assetctl/bin/assetctl skills sync --label staging --local-root .

# 3. push production（要先过 lint）
./agents/asset/cli/assetctl/bin/assetctl skills sync --label production --local-root .

# 4. 验证拉回字节正确
./agents/asset/cli/assetctl/bin/assetctl skills load --label production --local-root . --dest /tmp/loadtest
# 期望 envelope: results=23, 全部 source:"langfuse"
```

### 配套 lint 深修（bootstrap 过程发现，2 个 atomic commit）

production push 第一次失败：lint 卡 23/23 报 `missing frontmatter field allowed_tools`。根因不是 SKILL.md 错，是 lint 实现跟 Anthropic Skill spec 偏离。两个调研 agent 并发查（Anthropic 官方 docs + codex Rust loader + GitHub 上主流 skill 仓）得出：

- **codex 完全不读 `allowed-tools`** 字段：`codex-rs/core-skills/src/loader.rs:38-52` 的 serde struct 只 deserialize `name`/`description`/`metadata.short-description`。tool dependencies 走邻居文件 `agents/openai.yaml`，不是 SKILL.md frontmatter
- **Anthropic 自家 18 个 first-party skills + codex 自家 5 个 bundled samples + superpowers 14 个 skills 全部省略 `allowed-tools`** —— 此字段在 spec 上 optional，只 `description` 被 recommended
- **Anthropic docs** 文字接受**空格分隔 scalar** 或 **YAML list**，逗号分隔实际容忍但不在 spec
- **5 类 tool name 命名**（permission rule，不是 tool ID）：PascalCase 内建（`Read`/`Write`/`Bash`）/ scoped 内建（`Read(./.env)`、`Bash(cmd-glob)`、`WebFetch(domain:x)`）/ MCP（`mcp__server__tool`）/ Agent（`Agent(name)`）/ 项目自有 atomic（lowercase-kebab）
- **`Bash(逗号 list)` 是非法语法**：Bash 括号里只能是**单个**命令 pattern，要拆成 `Bash(cmd:*) Bash(cmd:*)`

两个 atomic commit 落 main：

| Commit | 改 | 内容 |
|---|---|---|
| `d4f6900` fix(assetctl) | `vendor/assetctl/internal/skills/lint.go` + 4 个 test 文件（526 insert / 95 delete） | parser 加 paren-aware comma/space split scalar → list；`atomicToolIDSet` 硬卡换为 5-class structural validator（Builtin/ScopedBuiltin/MCP/Atomic/Unknown）；放宽到只 require `description`；加 11 个新测试覆盖各类形态；lint_test.go 含 `TestClassifyToolName` 表格测可观测各类边界（`""`、`"123abc"`、`"foo_bar"`、`"FooBar(..."`、`"mcp__only-one-segment"` 都正确归 Unknown） |
| `456177b` fix(adaptation) | `agents/adaptation/skills/{bible-reviewer,novel-evaluator}/SKILL.md` line 4 | `Bash(cat:*, wc:*, mkdir:*, ...)` 拆为多个 `Bash(cat:*), Bash(wc:*), Bash(mkdir:*), ...` —— 每个独立 entry 才能在 Claude Code 真的 pre-approve |

### 范式（本块沉淀）

- **不要发明本地 lint 标准**：跟 Anthropic 官方 + Anthropic 自家 examples 的最小公倍数对齐；deferral cost = 用 codex 真不读 / Anthropic 自己也省略的字段去卡作者，是 anti-pattern
- **frontmatter key allowlist** = codex `quick_validate.py:40` 已经确认的 `{name, description, license, allowed-tools, metadata, compatibility}`；超出的 key 会被 codex 拒（虽然 codex runtime 不读 allowed-tools，但作者侧 quick_validate 是 lint 的真实下游）
- **同 prompt 名跨 label = 同字节才安全**：staging label 上次 push 是 lint 修之前的旧字节，production 是修后字节 —— 出现"跨 label drift"。这次顺手补：把 2 个 fixed SKILL.md 用 `--name` 单 push 到 staging label（v3）回到一致

## 已知 follow-up（不在本次 merge 范围）

- **pre-existing gofmt drift**：`vendor/assetctl/internal/tools/{ossput,sfxelevenlabs,suno}/_test.go` 在上 wave camelCase 修改后没 gofmt，main 一直带着；本 branch 不动，留给独立 hygiene PR
- **`makeRepo()` 调用方的旧 6 测试 temp dir 不清理**：本 branch 只清了 S2+S4 新加的 7 个测试的 temp dir；剩 6 个老 `makeRepo()` 用户（覆盖在 `test/workshop-codex-home.test.mjs` + 同目录其他 `.test.mjs`）有同样的问题，独立 hygiene PR 一起扫
- **`context.Background()` no timeout in `skills load` + `skills sync`**：Go 层两边都没 timeout；spec reviewer 建议加 30s context，需要时跨 sync/load 一起改
- **`sync --check --label X` 不尊重 `--label` 参数**：`sync.go:191` 硬编码 `s.Client.GetPrompt(ctx, s.Endpoint, name, "production")` —— 不管 `--label staging` 还是 `--label production` 都查 production label。本块发现的小 bug，不影响 skill 内容/lint/运行时，独立 hygiene PR 修
- **D5 `_shared/knowledge/codex-home.ts` 复制路径决策**：当前候选 (c) 用 repo-absolute path（不复制到 staging）；future D5 final 可能要 codex 真的 copy `_shared/knowledge/` 到 staging，这是 **Block 4 范畴**（未启动）

## push 状态

- **lunaverse-ide main @ `456177b`**：本地，cdotlock/lunaverse-ide 远端**未推送**（合计 86 commit 未推 = Wave 3-5 + Wave 4 doc + Block 2/3 fleet + camelCase 3 + Wave 5 10 + Block 2/3 IDE handoff 23 + lint 深修 + SKILL.md fix 2）
- **mob-wiki main**：本地新增本次更新，cdotlock/mob-wiki 远端**未推送**
- 用户 2026-05-20 表态"暂不 push，先干活"

## 工作机器（沿用 Wave 1-5 + foundation 模式）

1. 单 slice 设计 spec / plan（已有，本次跳过）→ 派 fresh subagent 实现 → 双段评审（spec compliance + code quality）→ atomic follow-up commit（永不 amend）→ controller TRIAGE（真问题修，超范围驳回）
2. 跨 slice 用 worktree 隔离（`feat/block-2-3-ide-handoff` @ `/Users/august/.config/superpowers/worktrees/lunaverse-ide/feat-block-2-3-handoff`，保留作回滚兜底）
3. 完成后 FF merge main + wiki ingest + RESUME 更新
4. wiki + main push 都 gated，要明确同意
