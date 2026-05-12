---
title: mob-mini-agent
tags: [agent, pi, foundation, runtime, observability]
sources: [https://github.com/cdotlock/mob-mini-agent, /Users/Clock/moonshort/mob-mini-agent/README.md, /Users/Clock/moonshort/mob-mini-agent/pi/packages/foundation/docs/agent-foundation-practices.md, /Users/Clock/moonshort/backend/services/dream-agent/LESSONS-LEARNED.md]
created: 2026-05-04
updated: 2026-05-12
---

`mob-mini-agent` 是 Mob / Moonshort 的公司级 Agent foundation。它从公开项目 fork 起步，但当前目标不是复制上游产品，也不是把某个业务 agent 服务整包搬进来；它的职责是把我们在真实生产 agent 中验证过的 runtime 升级、上下文纪律、skills 机制、观测方式和 provider 适配沉淀成可复用基础设施。

2026-05-12，`smolagent` tag 标记历史边界；之后仓库正式转向 Pi agent core。旧兼容层已经从主线删除，当前主线只保留 Pi/TypeScript 底座和公司 foundation package。

## 当前状态

关键提交：

| 提交 | 含义 |
| --- | --- |
| `smolagent` tag | 最后一个旧底座版本，作为历史查看边界。 |
| `8bd3268` | Pi 迁移起点空提交。 |
| `99b109a` | 迁入 Pi runtime baseline。 |
| `02f1a53` | 删除 Pi 应用层包，只保留 `ai` / `agent` / foundation 工作面。 |
| `601edd8` | 新增 `@moonshort/mob-agent-foundation`。 |
| `08b00c8` | 删除旧兼容源码、旧测试、旧 docs、旧 CI、E2B 配置和应用层脚本。 |
| `b01ee17` | 增加通用 run observability diagnostics 和踩坑根因文档。 |

当前保留：

- `pi/packages/ai`：统一多 provider LLM API 和 provider adapter。
- `pi/packages/agent`：Pi agent core、tool execution、session/harness、message/compaction primitives。
- `pi/packages/foundation`：Moonshot 生产经验沉淀成的 domain-neutral runtime utilities。

当前不保留：

- 业务 controller / job runner / backend client。
- Dream-specific prompts、skills、MSS、artifact schema。
- coding app、terminal UI、web UI 等应用层产品。
- 旧源码、旧测试、旧多语言文档和旧 CI。

## Foundation Package

路径：`/Users/Clock/moonshort/mob-mini-agent/pi/packages/foundation`

| 模块 | 作用 |
| --- | --- |
| `facts-anchor.ts` | 从权威状态生成 facts anchor；compact 前 strip 旧 anchor，compact 后注入新 anchor。 |
| `final-answer.ts` | typed terminal final-answer tool，避免自由文本 final 被 thinking 预算饿死。 |
| `compaction.ts` | prune 大 tool result、compact 旧上下文、连续失败 circuit breaker。 |
| `observability.ts` | `logEvent` / `logMetric` / `logTrace`、per-run JSONL、`AgentRunObserver`、stuck-loop detection、runtime facts 渲染。 |
| `runtime-overrides.ts` | maxTokens 和 thinking level 的 per-call override slot。 |
| `role-routing.ts` | 按角色选择 model tier 和 thinking level。 |
| `repr-parser.ts` | historic repr-style payload 的 ingestion-edge parser；新 prompt 不应依赖它。 |
| `messages.ts` | AgentMessage 的 role/text/token helper。 |

## 生产踩坑沉淀

这些规则来自正式版 `backend/services/dream-agent` 的迁移和 smoke runs。

### Facts Anchor 优先于 Summary

症状：多次 compact 后，agent 重做已完成工作、漏掉缺失 review、误读预算或 verdict。

根因：LLM summary 是叙事压缩，不是事实存储。ids、counts、hashes、verdicts、budgets、recent errors 会在反复 summarise 中衰减。

底座规则：每轮从业务权威状态计算 facts anchor；anchor 是 facts，不是 decisions。agent 仍然自主决定下一步。

### Terminal Emit 必须是 Tool

症状：模型 reasoning 很长，最终 assistant text 为空或无法解析。

根因：thinking、text、tool-use 共享响应预算。

底座规则：最终状态用 typed tool call 承载，runtime 读取 tool payload 作为 canonical final result。

### maxTokens 必须显式

症状：高 thinking role 经常空返回或提前截断。

根因：provider 默认输出上限可能远低于模型硬上限。`maxTokens` 是 cap，不是费用承诺。

底座规则：provider call 经 runtime policy 显式设置 maxTokens；需要 recovery 时用 per-call thinking override。

### State Machine 只守 Invariant

症状：同一个 tool 被反复调用，因为中间状态迁移被拒绝，但 agent 只看到失败结果。

根因：状态机把业务顺序当成 gate，造成 liveness trap。

底座规则：状态机只拒绝 terminal-to-active / backward 这类 invariant；业务 prerequisite 放到 domain tool 或 runtime precondition，并把 rejection reason 写进 recent errors。

### Observability 是 Runtime 核心功能

症状：几小时 run 失败，只能在混杂 stdout/stderr 里人工找根因。

根因：没有 per-turn trace、tool-call timeline、compaction event、run summary、per-run JSONL。

底座规则：每个逻辑单位一条结构化 JSON event：

- `kind:"turn"`
- `kind:"tool_call"`
- `kind:"compaction"`
- `kind:"stuck"`
- `kind:"run.summary"`

本地和 on-call 可通过 `AGENT_TRACE_DIR` 写 per-run JSONL。

### Agent 要能看见自己的 Debug Tail

症状：operator 能从日志看出 loop，agent 自己却不知道刚刚连续失败。

根因：recent tool calls 和 recent errors 只存在于日志，不在模型上下文。

底座规则：`AgentRunObserver` 维护 bounded ring buffer，并通过 `renderRuntimeDiagnosticFacts(snapshot)` 放进 facts anchor：

```text
- runtime: run=run_123 turn=47 tool_calls=61 errors=3 compactions_failed=0 compact_circuit_open=false
- recent_tool_calls: writer(412ms) -> reviewer[ERR](120ms) -> reviewer[ERR](118ms) -> reviewer[ERR](115ms)
- recent_errors:
  - [tool:reviewer] illegal transition: active writer state cannot enter review
- stuck_warning: tool 'reviewer' returned isError=true 3 times in a row; stop retrying blindly and pivot from recent_errors
```

### Retry Loop 必须有 Circuit Breaker

症状：compaction LLM 失败后下一轮继续触发 compact，形成自我 DoS。

根因：上游 LLM retry 没有失败阈值。

底座规则：连续失败达到阈值后开 circuit，并把 `compactions_failed` / `compact_circuit_open` 暴露给 operator 和 agent。

### Role Routing 不能一刀切

症状：修复、格式化、schema patch 这类任务在高 thinking 模型上耗时过高。

根因：所有 role 共用一个 model tier 和 thinking level。

底座规则：creative / review role 可以高 thinking；repair / syntax / formatting role 默认 fast tier + off/minimal。

## 接入方式

新业务 agent 基于这个底座时，优先完成这些结构：

1. 用 `pi/packages/ai` 接 provider，不直接散落 SDK glue。
2. 用 `pi/packages/agent` 跑 agent loop 和 tool execution。
3. 在业务状态上构造 facts snapshot，再用 `buildFactsAnchorMessage` / `prependFactsAnchor` 注入。
4. 用 `AgentContextCompactor` compact 旧上下文，且 compact 前 strip anchors。
5. 用 typed final-answer tool 终止任务。
6. 用 `AgentRunObserver` 记录每轮、每个 tool、每次 compact 和最终 summary。
7. 把 `renderRuntimeDiagnosticFacts(observer.snapshot())` 合并进 facts anchor。
8. 用 `resolveRoleRoute` 这类 policy helper 做 role routing。

## 开发命令

```bash
cd /Users/Clock/moonshort/mob-mini-agent/pi
npm ci
npm run check
npm test --workspace @moonshort/mob-agent-foundation
npm run build --workspace @moonshort/mob-agent-foundation
```

## 边界原则

`mob-mini-agent` 的长期方向：

1. 保留公开项目 fork 的底层能力，不把 upstream 改成业务平台。
2. 在 `pi/packages/foundation` 放公司实践层。
3. 业务服务通过 foundation 组合能力，不复制 Dream Agent 代码。
4. 所有 domain-specific prompt、controller、job、artifact、backend API 留在业务仓库。
5. 对通用 runtime pattern 写测试，避免靠经验口口相传。

## 相关页面

- [[entities/mobai-agent]]
- [[concepts/server-layer]]
- [[concepts/four-layer-philosophy]]
- [[concepts/dreaming-universe]]
