---
title: mob-mini-agent
tags: [agent, pi, smolagents, foundation, runtime]
sources: [https://github.com/cdotlock/mob-mini-agent, /Users/Clock/moonshort/mob-mini-agent/README.md, /Users/Clock/moonshort/backend/services/dream-agent]
created: 2026-05-04
updated: 2026-05-12
---

`mob-mini-agent` 是 Mob / Moonshort 的通用 Agent 底座项目。它从公开项目 fork 起步，但目标不是复制上游产品，也不是把某个业务 agent 服务整包搬进来；它的职责是把我们在真实生产 agent 中验证过的小型 runtime 升级、上下文纪律、skills 机制、观测方式和 provider 适配沉淀成可复用基础设施。

2026-05-12 起，`smolagent` tag 标记最后一个以 Python `smolagents` 为正式底座的版本。该 tag 之后，仓库进入 Pi agent core 迁移线：旧 Python 兼容层仍保留，新的 TypeScript 底座集中在 `pi/`，并通过 `@moonshort/mob-agent-foundation` 承接正式版 `backend/services/dream-agent` 中可通用化的生产经验。

## 项目定位

`mob-mini-agent` 是公司级 Agent foundation，而不是业务 agent 本体。

它应该提供：

- agent loop 底座：provider-native function call、tool execution、streaming event、session / harness。
- 通用上下文管理：代码装配 context、事实锚点、compact、strip-before-compact、overflow retry。
- 通用 runtime 纪律：terminal emit tool、按角色 thinking/model routing、max token 显式配置、retry circuit breaker。
- 可复用能力系统：`SKILL.md` discovery、autoload、lookup、resource path guard。
- 轻量 adapter：LiteLLM / MCP / HTTP server / structured logs，只做薄封装，不成为平台级编排器。

它不应该提供：

- Dream Agent 的故事生产 controller。
- 业务 checkpoint / job runner / backend client。
- `coding-agent` / TUI / Web UI 这样的应用层产品。
- Langfuse、数据库、队列、生产部署的强绑定。
- 任何硬编码业务状态机。

这个边界很重要：`backend/services/dream-agent` 是生产业务服务；`mob-mini-agent` 只吸收其中跨业务复用的组件和经验。

## Git 和迁移边界

关键历史标记：

| 标记 / 提交 | 含义 |
| --- | --- |
| `original-smolagents` | 压缩后的 Hugging Face `smolagents` 上游基线。 |
| `smolagent` | 最后一个以 smolagents 为正式底座的本地版本。 |
| `chore: mark pi framework migration start` | Pi 迁移线起点空提交。 |
| `feat(pi): import pi runtime baseline` | 初始迁入 Pi 源码基线。 |
| `chore(pi): trim workspace to core packages` | 纠偏：删除应用层包，只保留 core `ai` / `agent`。 |

旧 Python 兼容层仍在：

- `src/smolagents`：上游 fork 保留区。
- `src/mobmini`：Mob Python 兼容层，提供旧版 agent profiles、skills、context assembly、LiteLLM、MCP、FastAPI adapter。

新 TypeScript 底座在：

- `pi/packages/ai`
- `pi/packages/agent`
- `pi/packages/foundation`

## Pi 工作区

`pi/` 是当前 TypeScript runtime 工作区。它不是 Pi monorepo 镜像，而是收敛后的基础包集合。

### `@earendil-works/pi-ai`

路径：`pi/packages/ai`

职责：

- 统一多 provider LLM API。
- 标准化模型元数据、provider stream options、thinking level、usage 和 tool call message 格式。
- 提供 OpenAI、Anthropic、Google、Bedrock、Mistral、DeepSeek、OpenRouter 等 provider adapter。
- 为 `pi-agent-core` 提供底层 `streamSimple()` 与 message / tool 类型。

在 foundation 中的定位：provider substrate。业务服务不应绕过它直接写 provider SDK glue，除非是新增 provider adapter。

### `@earendil-works/pi-agent-core`

路径：`pi/packages/agent`

职责：

- `Agent`：有状态 agent wrapper，持有 system prompt、model、thinking level、tools、messages、streaming state。
- `agent-loop`：处理 prompt、continue、assistant stream、tool execution、turn lifecycle。
- tool execution：支持 sequential / parallel，支持 `beforeToolCall`、`afterToolCall`、`terminate`。
- harness：session、skills、prompt templates、execution env、system prompt formatting、context transform hooks。
- session storage：JSONL / memory storage，支持 tree entry、message entry、compaction entry、branch summary entry。

本包暴露的缺口：session storage 使用 `uuid`，因此 `uuid` 必须是 `pi-agent-core` 的直接 dependency，不能依赖上层应用间接带入。

### `@moonshort/mob-agent-foundation`

路径：`pi/packages/foundation`

职责：把正式版 `backend/services/dream-agent` 的生产经验抽象成 domain-neutral utility。它不包含 Dream-specific controller、prompt、skills、MSS、backend HTTP client 或 job runner。

当前组件：

| 模块 | 来源经验 | 通用能力 |
| --- | --- | --- |
| `facts-anchor.ts` | Pass 6 persisted-artifacts anchor | 每轮从权威状态重新注入事实，避免 LLM compact 丢失 ids / counts / hashes / errors。 |
| `final-answer.ts` | Pass 5 `emit_final` tool | 用 typed terminal tool 结束任务，避免 thinking 占满 token 后没有 text final answer。 |
| `compaction.ts` | Pass 8 compact circuit + strip anchor | prune 大 tool result、compact 旧 history、strip re-injected anchors、连续失败后开 circuit。 |
| `observability.ts` | Pass 8 JSONL trace | 结构化 `logEvent` / `logMetric` / `logTrace`，可写 per-run JSONL trace file。 |
| `runtime-overrides.ts` | Pass 4/5 streamFn maxTokens + thinking override | 用 closure slot 给单次调用覆盖 maxTokens / thinking，不 fork core。 |
| `role-routing.ts` | Pass 5 per-role thinking / fast tier | 让创作、评审、修复、格式化等角色按策略选择 model tier 和 thinking level。 |
| `repr-parser.ts` | specialist payload compatibility | 把 Python repr 风格 dict/list 转成 JSON，兼容旧 specialist 输出。 |
| `messages.ts` | compactor / anchor helper | 统一从 AgentMessage 提取 role、text 和估算 token。 |

配套文档：

- `pi/packages/foundation/docs/agent-foundation-practices.md`

## 从正式版 Dream Agent 抽出的关键实践

这些实践来自 `/Users/Clock/moonshort/backend/services/dream-agent/LESSONS-LEARNED.md` 和对应实现代码。

### 1. Facts Anchor 优先于 lossy summary

长寿 agent 的上下文 compaction 不能承担“事实存储”职责。LLM summary 会逐轮损耗 episode id、hash、verdict、预算、错误次数等枚举事实。

正确模式：

1. 业务层从权威状态生成 facts snapshot。
2. runtime 把 snapshot 渲染成固定结构的 anchor message。
3. compact 前 strip 掉旧 anchor。
4. compact 后重新 prepend 最新 anchor。
5. agent 从 facts 决策下一步，但 framework 不硬编码决策。

这保留了 agent 自主性：framework 注入事实，不注入“下一步应该调用哪个工具”。

### 2. Terminal emit 必须是 tool

thinking-enabled provider 可能输出大量 reasoning，导致 text channel 没有足够 token 承载最终 JSON。Dream Agent 的修复是恢复 `final_answer` / `emit_final` 工具语义。

通用规则：

- 终态必须通过 typed tool call 表达。
- tool result 带 `terminate: true`，让 agent loop 停止自动 follow-up。
- terminal payload 应包含 `status`、`error`、`artifacts`。
- 不解析自由文本 JSON 作为主路径。

### 3. maxTokens 显式配置

provider 默认 `max_tokens` 不是可靠工程边界。对 DeepSeek v4 这样的长 thinking 模型，默认值可能导致 thinking 把输出预算耗尽。

通用规则：

- 在 runtime 层显式传 `maxTokens`。
- 把 maxTokens 当 cap，不当 cost control。
- 需要局部关闭 thinking 时，通过 streamFn closure slot 做 per-call override。

### 4. State machine 是 invariant，不是业务流程 gate

Dream Agent 生产问题说明，过严的 backend 状态迁移会造成 agent liveness 问题。状态机应该禁止 backward / terminal-to-active 这类 invariant 破坏，但不应强制业务必须按某个固定顺序调用 tool。

通用规则：

- “不能从 done 回 active”属于状态机。
- “写完才能评审”属于 domain runtime 或 tool precondition。
- workflow ordering 应作为 facts + tool error 暴露给 agent，让 agent 自主修正。

### 5. Observability 是 agent runtime 的核心功能

长寿 agent 的 stdout 不够调试。需要每轮、每个 tool call、每次 compact、每次 circuit 状态、最终 run summary 都有结构化 JSON。

通用规则：

- 逻辑单位一条 JSON event。
- per-run JSONL trace file 用于本地和 on-call。
- trace 信息也应能进入 facts anchor，让 agent 自己看到 recent errors 和 stuck warning。

### 6. Role routing 不应一刀切

创作、规划、评审、修复、格式化不是同一种模型任务。Dream Agent 中 `mss_repair` 用 high thinking 的成本和延迟都不合理，切到 fast tier / thinking off 后明显改善。

通用规则：

- creative roles 可以 high / xhigh。
- review roles 可以 high。
- repair / syntax / formatting roles 默认 fast + off。
- routing 是 policy，不是业务服务里的硬编码分支。

### 7. Compact retry 要有 circuit breaker

summary LLM 失败后原样返回上下文会在下一轮继续触发 compact，形成自我 DoS。Foundation compactor 保留连续失败计数，超过阈值后开 circuit，并把状态暴露给上层。

通用规则：

- 所有上游 LLM retry loop 都要有阈值。
- circuit state 必须可观测。
- circuit state 应能作为 facts 告知 agent。

## Python 兼容层

Python 层仍然存在，主要用于旧调用方和轻量嵌入式场景。

### Function-call-first core

`build_toolcalling_agent()` 基于上游 `ToolCallingAgent`，额外处理：

- `AgentSpec`：声明 agent 名称、描述、instructions、tools、skills、max steps。
- 默认 build / plan / explore / general agent profile。
- `final_answer` termination suffix。
- function-call 参数 coercion：object / array 被模型错误编码成 JSON string 时自动解码。
- `extract_final_answer()`：统一解开 `RunResult`、`AgentText`、JSON string、Python repr dict。

相关文件：

- `src/mobmini/agents.py`
- `src/mobmini/default_agents.py`
- `src/mobmini/runtime.py`
- `src/mobmini/tools.py`

### Skills

`SkillRegistry` 支持本地 `SKILL.md`：

- `auto_load` 全局注入。
- `auto_load_for` 按 agent 名称注入。
- `lookup_skill` tool。
- `lookup_skill_resource` tool。
- resource 路径逃逸保护。

相关文件：

- `src/mobmini/skills.py`

### Context 与 compact

Python 层已有：

- `ContextAssembler`：text / JSON block、priority、pinned、max chars。
- `CompactContextPolicy`：调用前压缩旧上下文。
- `MemoryCompactor`：运行中 prune / compact smolagents memory steps。
- context overflow retry hook。

这些能力未来应向 Pi foundation 的 facts anchor / compaction policy 对齐。

## 当前开发命令

Python 兼容层：

```bash
PYTHONPATH=src python -X faulthandler -m pytest -p no:capture -o addopts='' tests/test_mobmini_*.py -q
PYTHONPATH=src python -m ruff check src/mobmini tests/test_mobmini_*.py
```

Pi foundation：

```bash
cd pi
npm install
npm run check
npm test --workspace @moonshort/mob-agent-foundation
npm run build --workspace @moonshort/mob-agent-foundation
```

## 架构边界

`mob-mini-agent` 的长期方向是：

1. 保留公开项目 fork 的低层能力，不把 upstream 改成业务平台。
2. 在 `pi/packages/foundation` 放公司实践层。
3. 让业务服务通过 foundation 组合能力，而不是复制 Dream Agent 代码。
4. 把所有 domain-specific prompt、controller、job、artifact、backend API 留在业务仓库。
5. 对通用 runtime pattern 写测试，避免靠经验文档口口相传。

## 相关页面

- [[entities/mobai-agent]]
- [[concepts/server-layer]]
- [[concepts/four-layer-philosophy]]
- [[concepts/dreaming-universe]]
