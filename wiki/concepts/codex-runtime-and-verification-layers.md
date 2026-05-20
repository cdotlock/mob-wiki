---
title: codex 运行时（IDE 内） — auth 模型 + 验证层级
created: 2026-05-21
updated: 2026-05-21
tags: [moonshort-ide, codex, agent-adapter, auth, verification, codex-shim]
status: draft
---

# codex 运行时（IDE 内） — auth 模型 + 验证层级

把 IDE 里 codex 怎么起、auth 怎么传、各层怎么验证写清楚。**避免再有人按"独立 codex CLI"的思路去搞 `codex login` / `~/.codex/auth.json`**——IDE 里 codex 完全不走那条路。

> 关联：[[concepts/assetctl-skills-sync-and-staging]]（codex 读到的 SKILL.md 怎么来的）· [[concepts/moonshort-ide-ai-integration]]（IDE 整体 AI 集成架构，Tab 补全 + Moonshort Agent 两个表面）

## 一句话

IDE spawn 一个 **vendored codex 0.130 二进制**，在它前面起一个**本地 `codex-shim` HTTP 服务**当 OpenAI Responses API ↔ chat-completions 协议桥；通过环境变量 `MOONSHORT_AGENT_API_KEY` 注入 provider key；codex 连本地 shim，不连外网；CODEX_HOME 是**每次 run 现 stage 的 temp 目录**，跑完即清。

## 反直觉的事

| 直觉 | 真相 |
|---|---|
| codex 应该走 `codex login` / `~/.codex/auth.json` | ❌ IDE 完全绕过这套；auth 走 env var `MOONSHORT_AGENT_API_KEY` |
| codex 0.130 应该直连 OpenAI / DeepSeek 等 provider | ❌ codex 连 **localhost shim**；shim 负责调 provider |
| codex CODEX_HOME 应该是 `~/.codex/` | ❌ IDE 用 **run-private CODEX_HOME**：`/tmp/moonshort-codex-<runId>-XXXXXX/`，每次 run 起新的 |
| 跑 `codex exec` 命令行就能验证 IDE 链路 | ❌ 那条路径走 OpenAI Responses API 公网，会要 OpenAI 凭据；IDE 实际链路用的 shim+DeepSeek，**两条路径不重合** |

## Auth 模型（`packages/agent-adapter/src/backends/codex.ts:11-66`）

```typescript
// 文件: packages/agent-adapter/src/backends/codex.ts
const CODEX_API_KEY_ENV = "MOONSHORT_AGENT_API_KEY";

function codexEnv(config: AgentConfig): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env, [CODEX_API_KEY_ENV]: config.apiKey };
  if (config.codexHome) {
    env.CODEX_HOME = config.codexHome;
  }
  // ... prepend PATH with codex's own ripgrep dir + Workshop's tool dirs
}
```

`config.apiKey` 来自三层 fallback（最高优先 → 最低）：

1. **host 注入的 `moonshort.agent.apiKey`** — VS Code settings 之类的 settings lookup
2. **process env** — `MOONSHORT_AGENT_API_KEY` 已经在父进程环境里
3. **workspace 根的 gitignored `.env`** — 仅本机配置，永不入仓（spec §7.4）

> 详见 `packages/mss-workshop/src/agent-config.ts` 里的 `loadAgentConfig` 实现。

## codex-shim 的角色（`packages/agent-adapter/src/codex-shim.ts`）

**为什么需要**：codex 0.130 唯一支持的 model API 是 OpenAI **Responses API**（`POST /responses` + SSE）。DeepSeek、Anthropic 等只懂 **chat-completions**——直连过不去。

**shim 在做什么**：

1. `startCodexShim(config)` 在 loopback `127.0.0.1:<random-port>` 起一个 `node:http` server
2. codex 通过 `model_providers.*.base_url` 指向 `http://127.0.0.1:<port>`，append `/responses`
3. shim 接到 codex 的 `POST /responses`，**翻译**成 chat-completions 调 `config.baseUrl`（如 `https://api.deepseek.com`）
4. provider 的 chat-completions 回包再**翻译**回 Responses API SSE 事件流给 codex

**结果**：upstream codex 二进制零修改、不装额外 npm 包、不出 loopback。

## Vendored codex 二进制

由 `fork/build.mjs` 的 `stageVendoredCodex` 把仓库根 `vendor/codex/` 复制到 `<extension>/vendor-codex/`，路径形状：

```
<extension>/vendor-codex/vendor/<triple>/codex/codex
```

| 平台 | triple |
|---|---|
| macOS arm64 | `aarch64-apple-darwin` |
| Windows x64 | `x86_64-pc-windows-msvc` |
| 其他 | 无 vendored → fallback 到 `PATH` 上的 `codex`，再 fallback 到 ChatBackend（非 codex 路径） |

`codexCommand(config)` 永远优先 `config.codexPath`（host 计算好的绝对路径），裸 `"codex"` 只是非 IDE caller 的最后兜底。

### 开发机替身

如果你本机装了 cline VS Code 扩展，cline 自带同版本 codex：

```
/opt/homebrew/lib/node_modules/cline/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/codex/codex
```

`tools/verify-skill-discovery.mjs` 接受 `MOONSHORT_AGENT_CODEX_PATH=<path>` 覆盖，开发期可直接用这个跑离线 verify，不必先 build `.app`。

## CODEX_HOME staging（spec §3.1 + §5.6）

**run-private**：每次 codex run 现 stage 一个 temp 目录：

```
/tmp/moonshort-codex-<runId>-XXXXXX/
├── skills/
│   ├── <skill-1>/SKILL.md   ← Pass 1 cp local + Pass 2 Langfuse overlay
│   ├── <skill-1>/references/...
│   ├── <skill-1>/scripts/...
│   └── ...
└── AGENTS.md  ← agent identity + 一行 "your skills are in skills/..."
```

`packages/mss-workshop/src/codex-home.ts` 的 `stageCodexHome(agent, agentDir, sharedDir, runId, options)`：

1. `mkdtemp` 一个 temp CODEX_HOME
2. `stageSkills(agentDir, sharedDir, codexHome, options)`：
   - **Pass 1** — `cp -r` 把 `<agentDir>/skills/*` 和 `<sharedDir>/skills/*` 复制进 `<codexHome>/skills/`（agent 的赢同名冲突）
   - **Pass 2** — spawn `assetctl skills load --label production --dest <codexHome>/skills`，把每个 SKILL.md body 用 Langfuse production label 内容覆盖；任何失败静默回退 Pass 1 的本地字节（spec §2.1 D1 invariant）
3. 写 `AGENTS.md` 装 agent 的 standing instructions
4. 返回 `{ codexHome, catalog, cleanup() }`；caller 在 run 结束（成功/失败）调 `cleanup()` 把 temp 目录删掉

**为什么 run-private**：agent A 的 skill 永远不会跨进 agent B 的 codex run；并发 run 用 runId 区分目录名零冲突。

## 验证层级

| 层 | 跑什么 | 需要什么 | 验什么 |
|---|---|---|---|
| **L0 单测** | `pnpm test`（覆盖 `test/workshop-codex-home.test.mjs`、`test/workshop-cli.test.mjs`、`test/agent-adapter*.test.mjs`） | 无 | stageSkills / stageCodexHome / agent-adapter 函数级正确性；用 fake assetctl 二进制走 spawn 接口 |
| **L1a 离线 skill discovery** | `MOONSHORT_AGENT_CODEX_PATH=<codex> node tools/verify-skill-discovery.mjs` | 真 codex 二进制 + 仓库 `agents/asset/` + `agents/_shared/`；**不需要 API key** | codex 0.130 真的扫 `$CODEX_HOME/skills/` + 把目录吐进 model-visible prompt input；新 skill folder drop-in 不改 `agent.json` 也立即被发现 |
| **L1b Langfuse overlay 字节落地** | 设 `LANGFUSE_HOST`/`PUBLIC_KEY`/`SECRET_KEY` 再跑 L1a；之后 diff `<staged>/skills/<name>/SKILL.md` vs `agents/<id>/skills/<name>/SKILL.md` | Langfuse staging 或 production 凭据 | overlay 真把字节换了（确认 assetctl spawn + Langfuse 拉取 + 写盘整条链） |
| **L2a LLM-in-the-loop auth+transport** | `tools/verify-l2-smoke.mjs` — 跑两段：ChatBackend 直连 chat-completions + CodexBackend 经 codex-shim bridge | `MOONSHORT_AGENT_API_KEY` + `_BASE_URL` + `_MODEL` + `_CODEX_PATH`（可选） | 验 provider 接受 key+model、codex-shim Responses↔chat-completions 桥工作 |
| **L2b LLM-in-the-loop agentic 任务** | `tools/verify-workshop-agent.mjs`（Workshop EXECUTE stage 端到端：executeInstruction → ChatBackend → extractJson → applyPromptMap）；之后 IDE Production Workshop UI 跑真业务 | 同 L2a；UI 形态另需已 build 的 `.app` 或 dev 模式 + mss CLI on PATH | agent 真推理 → 返回 JSON prompt map → runner 解析并写回每个 asset 的 prompt + status |

### L0 跑法

```
cd /Users/august/MobAI/moonshort-ide
pnpm test
```

### L1a 跑法（已验，2026-05-21）

```
MOONSHORT_AGENT_CODEX_PATH=/opt/homebrew/lib/node_modules/cline/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/codex/codex \
node tools/verify-skill-discovery.mjs
```

预期输出：

```
codex:  /opt/homebrew/...
[1] host staged a run-private CODEX_HOME
    catalog: asset-prompt-generator, asset-renderer, asset-reviewer, cg-render-spec, ...（15 个）
[2] codex surfaced all 15 agent skill(s) in the model-visible input
    ## Skills ...
[3] dropped a new skill folder (no agent.json edit) — discovered + surfaced
Verification PASSED — the capability-folder model works end to end.
```

### L1b 跑法

```
export LANGFUSE_HOST=https://prompt.mobai-game.com
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
MOONSHORT_AGENT_CODEX_PATH=<codex> node tools/verify-skill-discovery.mjs

# 然后从输出里的 staged CODEX_HOME 路径 diff 至少一个 SKILL.md
# vs agents/asset/skills/<name>/SKILL.md，确认字节被换
```

### L2a 跑法（已验，2026-05-21 — 团队实际用 mob-ai 而非 DeepSeek）

```
export MOONSHORT_AGENT_API_KEY=<MOB_AI_API_KEY 的值>   # 在 assets-produce/.env 里
export MOONSHORT_AGENT_BASE_URL=https://ai.mob-ai.cn/api/v1
export MOONSHORT_AGENT_PROVIDER=mob-ai
export MOONSHORT_AGENT_MODEL=deepseek-v4-flash       # 也可 deepseek-v4-pro / claude-sonnet-4-6 / gpt-5.5:free
export MOONSHORT_AGENT_CODEX_PATH=<codex 二进制>      # 没 build .app 时填，可借 cline 同版本

node tools/verify-l2-smoke.mjs
```

预期输出（2026-05-21 实跑结果）：

```
config: {"provider":"mob-ai","baseUrl":"https://ai.mob-ai.cn/api/v1","model":"deepseek-v4-flash","apiKey":"<redacted:…dd2f>","codexPath":"..."}

--- ChatBackend (direct chat-completions) ---
  session: agent-...-0
  output: "PONG"
  usage: {"inputTokens":42,"outputTokens":23}
  PASS — provider accepts our key + model.

--- CodexBackend (codex 0.130 → codex-shim → provider) ---
  session: agent-...-1
  progress: Codex protocol bridge ready.
  progress: Codex session started.
  progress: Codex turn started.
  progress: Codex turn completed.
  output: "PONG"
  PASS — codex harness ran end-to-end through the bridge.

L2 smoke PASSED.
```

### L2b 跑法（已验，2026-05-21）

```
# 同 L2a 的 env，再跑：
node tools/verify-workshop-agent.mjs
```

预期输出（2026-05-21 实跑结果）：

```
L2b smoke — Production Workshop EXECUTE stage
config: {"provider":"mob-ai","baseUrl":"https://ai.mob-ai.cn/api/v1","model":"deepseek-v4-flash",...}

--- Workshop EXECUTE backgrounds segment → live model ---
  session: agent-...-0
  output: 1079 chars
  usage:  {"inputTokens":6344,"outputTokens":356}
  background:bedroom → Anime-style bedroom interior at night, warm dusk tones, dim amber lampli…
  background:rooftop → Anime-style rooftop scene looking out over a sprawling city at dusk, war…

L2b smoke PASSED — EXECUTE stage produced usable per-asset prompts.
```

> **2026-05-21 hygiene**：原来三个 L2 live verify 脚本都坏了——`verify-shadow-codex.mjs` 引用了被删的 `packages/mss-workbench/out/src/shadow-workspace.js`，`verify-agent.mjs` 引用已删的 `buildInlineEditRequest`/`cleanInlineEditOutput`，`verify-workshop-agent.mjs` 引用已改名的 `applyPrompts`/`stageInstruction`。修了：前两个脚本 PONG 部分被 `verify-l2-smoke.mjs` 取代直接删；`verify-workshop-agent.mjs` 重写到新 `executeInstruction` API。同时发现 `extractJson` 用严格 `JSON.parse` 在 LLM 输出有 trailing comma 时会整盘丢——已经改成 strict → sanitized 两段 fallback（commit `037a2db`）。
>
> 更深的 agentic 路径（codex 真推理 → 选 skill → 调 assetctl → 写 shadow workspace → diff mss）需要 IDE Workshop UI 跑真业务，目前只能开 `.app` 或 dev 模式验证，没单独 verify 入口。

## 老 RESUME 笔记的坑

历史 RESUME-next-phase.md 里有一行"**codex 端到端实跑验证仍卡在 `~/.codex/auth.json` 不存在**"——**这是误判**。`codex exec` 在终端直接跑会走 OpenAI 公网 + 需要 OpenAI 凭据；那条路径 IDE 完全不用。正确的 L2 入口是 `tools/verify-l2-smoke.mjs`（L2a auth+transport）或 `tools/verify-workshop-agent.mjs`（L2b workshop EXECUTE stage）或 IDE UI，需要的是 `MOONSHORT_AGENT_API_KEY`（team 实际配 mob-ai 的 key），不是 OpenAI key。

2026-05-21 已在 `~/.config/superpowers/worktrees/moonshort-ide/RESUME-next-phase.md` 第 494 行修正。

## 代码参考表

| 关注点 | 文件 | 关键符号 |
|---|---|---|
| codex spawn / env / args | `packages/agent-adapter/src/backends/codex.ts` | `CodexBackend`, `codexCommand`, `codexEnv`, `codexArgs`, `CODEX_API_KEY_ENV` |
| codex-shim HTTP bridge | `packages/agent-adapter/src/codex-shim.ts` | `startCodexShim`, `handleRequest` |
| Agent config 三层 fallback | `packages/mss-workshop/src/agent-config.ts` | `loadAgentConfig`, `bundledCodexPath`, `parseDotEnv` |
| CODEX_HOME staging | `packages/mss-workshop/src/codex-home.ts` | `stageCodexHome`, `stageSkills`, `discoverSkills`, `agentsMd` |
| assetctl overlay spawn + TTL 缓存 | `packages/mss-workshop/src/assetctl-bridge.ts` | `loadSkillsViaAssetctl`, `clearAssetctlLoadCache` |
| Vendored codex 打包 | `fork/build.mjs` | `stageVendoredCodex`, `CODEX_TRIPLES` |
| L0 单测 | `test/workshop-codex-home.test.mjs`、`test/workshop-cli.test.mjs`、`test/agent-adapter*.test.mjs` | `stageSkills` / `stageCodexHome` / `CodexBackend` / `loadAgentConfig` |
| L1a 离线 verify | `tools/verify-skill-discovery.mjs` | `resolveCodex`, `promptInput`, `expectSurfaced` |
| L2a auth+transport verify | `tools/verify-l2-smoke.mjs` | `probeChatBackend`, `probeCodexBackend` |
| L2b workshop EXECUTE verify | `tools/verify-workshop-agent.mjs` | `executeInstruction`, `extractJson`, `applyPromptMap` |

## 验证状态（2026-05-21）

- ✅ L0 单测 — 全过（CI 持续验证）
- ✅ L1a 离线 — `tools/verify-skill-discovery.mjs` 跑通，`agents/asset` 15 skills 全部被发现 + 暴露给 codex prompt input
- ✅ L1b Langfuse overlay — 2026-05-21 B3-IDE-5 bootstrap 期间手动 `assetctl skills load --label production` → 23/23 from langfuse 成功；下次同步式 verify-skill-discovery 加 Langfuse env 再补一次双重验证
- ✅ **L2a LLM-in-the-loop auth+transport** — 2026-05-21 `tools/verify-l2-smoke.mjs` 跑通（mob-ai / deepseek-v4-flash / cline-bundled codex 0.130）；ChatBackend + CodexBackend 两段都 PONG，codex-shim Responses↔chat-completions 桥工作
- ✅ **L2b LLM-in-the-loop workshop EXECUTE stage** — 2026-05-21 `tools/verify-workshop-agent.mjs` 跑通（同 mob-ai 配置）；agent 真返回 JSON prompt map、`applyPromptMap` 把 prompt + status 写回 assets；顺手发现 `extractJson` 对 trailing comma 不容错（commit `037a2db` 改成 strict → sanitized 两段 fallback）
- ⏸️ L2b 更深的 agentic 路径 — codex 真推理 → 选 skill → 调 assetctl → 写 shadow workspace → diff mss 还没单独 verify 入口；需要 IDE Workshop UI 跑真业务，或新写一个 codex-host smoke

## 后续

- ~~修 3 个 stale verify 脚本~~ **2026-05-21 做完**：`verify-shadow-codex.mjs` 和 `verify-agent.mjs` 删除（shadow workspace 已删 / PONG 部分被 verify-l2-smoke 取代）；`verify-workshop-agent.mjs` 重写到 `executeInstruction` + `applyPromptMap` 并跑通 L2b。同时修了 `extractJson` 对 trailing comma 的容错（fix `037a2db`）
- 把 L1b 加进 `verify-skill-discovery.mjs`：可选 env `MOONSHORT_VERIFY_LANGFUSE=1` 时自动 diff overlay vs source 字节
- 把 L2a 改装成 CI smoke：用一个最小 stub provider 或 record/replay fixture，避开真 LLM 调用费用（可选）
- 把 codex 二进制路径默认值从 hardcoded `/Users/Clock/...` 改成相对仓库 path 探测（`tools/verify-skill-discovery.mjs:34`）—— `verify-l2-smoke.mjs` 已经按 vendored 路径探测了，可以照抄
- L2b 更深的 codex agentic 端到端 verify：codex 真推理 → 选 skill → 调 assetctl → 写 shadow workspace → diff mss。需要新写一个 codex-host smoke 或开 IDE Workshop UI 真业务
