---
title: assetctl skills sync + Block 2/3 staging（codex skill 加载链路）
created: 2026-05-20
updated: 2026-05-20
tags: [assetctl, block-2, block-3, codex, langfuse, skill-loader, skill-staging, moonshort-ide]
status: draft
---

# assetctl skills sync + Block 2/3 staging（codex skill 加载链路）

把 codex 内的 skill body **从本地 git 唯一源** 升级为 **Langfuse production label 优先 + 本地 git 兜底**。Block 2 = skill 内容/编排骨架；Block 3 = Langfuse-first loader + IDE wiring。两块在 2026-05-20 一起合 moonshort-ide main @ `266cd3c`。

> 设计 spec：
> - `moonshort-ide/docs/design/2026-05-20-block-2-orchestration-skill-spec.md`（472 行）+ `…plan.md`（619 行）
> - `moonshort-ide/docs/design/2026-05-20-block-3-langfuse-loader-spec.md`（372 行）+ `…plan.md`（438 行）
>
> 关联：[[concepts/assetctl-integration-contract]]（Block 1 原子能力契约）· [[entities/moonshort-ide]]

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
| `shot-image-from-mss` frontmatter ⊇ body 工具集 | ✅ 完成（本次） | B2-15 fix `b9a5f8f`：补全 `generate-video-happyhorse, crop-video` 两颗 fallback 工具授权 |
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
| CLI `skills sync` | B3-5 `e820202` | 子命令 + flag 解析 + env 读取（`LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`）+ MOONSHORT_SKILL_LANGFUSE_TTL_MS；exit code 推导（lint fail=4、drift=6、5xx=5、auth=4）；覆盖 85% |
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
| S2 · TS stageSkills 集成 | `14af858 feat` + `228b1e5 test` + 4 quality fix | `packages/mss-workshop/src/codex-home.ts` 两阶段流程：cp 本地文件夹 → spawn `assetctl skills load` 覆盖 SKILL.md → 解 envelope 记 `source:langfuse|local` per skill；`runCli` 重用（S2 quality fix 把 NIH `spawnAssetctlLoad` 收掉用 `runCli(binary, args, undefined, 0)`） |
| S3 · LANGFUSE_* 环境注入 | **零代码**（确认 `spawn` 默认继承 `process.env`）+ `266cd3c docs` | vendor/README 加 Block 3 env table |
| S4 · IDE-host TTL cache | `34d960a feat` + `3c1af68 test` + 4 quality fix | 提取 `packages/mss-workshop/src/assetctl-bridge.ts`（349 行）：模块级 `Map<cacheKey, {results, expiresAt}>`，key = `repoRoot:::agentDir:::sharedDir:::label`，TTL per-call 从 env 读（默认 60_000ms）；cache 存 SKILL.md body 字节（不光 envelope metadata）以保 §D byte-identity；失败不缓存（spec §F） |

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
| `MOONSHORT_SKILL_LANGFUSE_LABEL` | no（默认 `"production"`） | 加载哪个 Langfuse label |
| `MOONSHORT_SKILL_LANGFUSE_TTL_MS` | no（默认 `60000`） | IDE-host cache TTL（毫秒） |
| `ASSETCTL_BINARY` | no（默认 `<repoRoot>/agents/asset/cli/assetctl/bin/assetctl`） | binary 路径覆盖（测试/CI 用） |

任何 LANGFUSE_* 缺失 → `assetctl skills load` 静默回退本地 git body（spec §2.1 D1），envelope 返回 `source:"local"` for all skills，exit 0。

## Block 3 bootstrap 还没做（B3-IDE-5）

剩一件事：**首次把 15 个 skill push 到 Langfuse**（staging → production），让 IDE 可以真的从 Langfuse 拉到东西。这是手工 ops 步骤：

```
# 1. 在 IDE 主仓根目录
export LANGFUSE_HOST=prompt.mobai-game.com
export LANGFUSE_PUBLIC_KEY=<...>
export LANGFUSE_SECRET_KEY=<...>

# 2. push 到 staging（不 lint）
./agents/asset/cli/assetctl/bin/assetctl skills sync --label staging --local-root .

# 3. 确认 staging OK 后 push 到 production（开 lint）
./agents/asset/cli/assetctl/bin/assetctl skills sync --label production --local-root .

# 4. 验证：可以用 skills load 拉回来
./agents/asset/cli/assetctl/bin/assetctl skills load --label production --local-root . --dest /tmp/loadtest
# 期望 envelope 中所有 skill source = "langfuse"
```

触发条件 = 用户提供 Langfuse 凭据 + 同意做 bootstrap。当前 IDE wiring 已经 zero-config 就绪：env 设了走 Langfuse，不设走本地，二者同 byte。

## 已知 follow-up（不在本次 merge 范围）

- **pre-existing gofmt drift**：`vendor/assetctl/internal/tools/{ossput,sfxelevenlabs,suno}/_test.go` 在上 wave camelCase 修改后没 gofmt，main 一直带着；本 branch 不动，留给独立 hygiene PR
- **`makeRepo()` 调用方的旧 6 测试 temp dir 不清理**：本 branch 只清了 S2+S4 新加的 7 个测试的 temp dir；剩 6 个老 `makeRepo()` 用户（覆盖在 `test/workshop-codex-home.test.mjs` + 同目录其他 `.test.mjs`）有同样的问题，独立 hygiene PR 一起扫
- **`context.Background()` no timeout in `skills load` + `skills sync`**：Go 层两边都没 timeout；spec reviewer 建议加 30s context，需要时跨 sync/load 一起改
- **D5 `_shared/knowledge/codex-home.ts` 复制路径决策**：当前候选 (c) 用 repo-absolute path（不复制到 staging）；future D5 final 可能要 codex 真的 copy `_shared/knowledge/` 到 staging，这是 Block 4 范畴
- **B3-IDE-5 bootstrap push**：见上一节，等用户

## push 状态

- **moonshort-ide main @ `266cd3c`**：本地，cdotlock/moonshort-ide 远端**未推送**（合计 ~84 commit 未推 = Wave 3-5 + Wave 4 doc + Block 2/3 fleet + camelCase 3 + Wave 5 10 + 本次 23）
- **mob-wiki main @ `a94edb4`**：本地，cdotlock/mob-wiki 远端**未推送**（4 个 Block 1 doc commit + 本次新增）
- 本次 merge 不 push，用户 2026-05-20 表态"暂不 push，先干活"

## 工作机器（沿用 Wave 1-5 + foundation 模式）

1. 单 slice 设计 spec / plan（已有，本次跳过）→ 派 fresh subagent 实现 → 双段评审（spec compliance + code quality）→ atomic follow-up commit（永不 amend）→ controller TRIAGE（真问题修，超范围驳回）
2. 跨 slice 用 worktree 隔离（`feat/block-2-3-ide-handoff` @ `/Users/august/.config/superpowers/worktrees/moonshort-ide/feat-block-2-3-handoff`，保留作回滚兜底）
3. 完成后 FF merge main + wiki ingest + RESUME 更新
4. wiki + main push 都 gated，要明确同意
