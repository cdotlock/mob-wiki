---
title: mob-mini-agent
tags: [agent, smolagents, python, function-call, subagent, skills, mcp, litellm, fastapi]
sources: [https://github.com/cdotlock/mob-mini-agent, /Users/Clock/moonshort/mob-mini-agent/README.md, /Users/Clock/moonshort/backend/services/dream-agent]
created: 2026-05-04
updated: 2026-05-04
---

`mob-mini-agent` 是 Mob 的轻量嵌入式 mini-agent 框架。它基于 Hugging Face `smolagents`，保留上游小核心，并在旁边新增 `mobmini` 层，把 [[concepts/dreaming-universe]] / `dream-agent` 中验证过的 function-call agent 经验沉淀成通用基建。

## 定位

`mob-mini-agent` 不是完整编排平台，而是可嵌入到任意 Python 服务里的 agent kernel。它更接近 OpenCode / Claude Code 式的最小 agent 运行层：模型负责 function call，框架负责工具表面、上下文、skills、subagent 和少量 runtime 纪律。

核心取向：

- 默认走 provider-native function call。
- subagent 是普通 tool，而不是独立调度系统。
- skills 由本地 `SKILL.md` 管理。
- task context 由代码装配，不把状态拼接逻辑散在 prompt 里。
- provider 接入以 LiteLLM 为主。
- FastAPI / MCP / observability 都是薄 adapter，不成为硬依赖。

## 与上游 smolagents 的关系

仓库保留上游 `src/smolagents` 作为底座。Git 历史被整理成一个压缩后的上游基线加 Mob 增量：

```text
original-smolagents  原版 smolagents 基线
mob-mini-agent       Mob 增量提交
```

`original-smolagents` tag 标记原版基线。Mob 自己新增的框架代码集中在 `src/mobmini`。

当前 Mob 框架源码规模，不含 README、元数据和 tests：

| 范围 | 行数 |
| --- | ---: |
| `src/mobmini/*.py` | 1345 |

复算命令：

```bash
wc -l src/mobmini/*.py
```

## 新增能力

### Function-call-first core

`build_toolcalling_agent()` 基于上游 `ToolCallingAgent`，加入 Mob 默认纪律：

- 内置 4 种默认 agent profile。
- `AgentSpec`：声明 agent 名称、描述、指令和最大 step。
- skills catalog / auto-loaded skill 注入。
- termination suffix：要求模型完成任务时通过 `final_answer` 返回。
- `extract_final_answer()`：统一处理 `RunResult`、`AgentText`、JSON string 和普通值。
- function-call 参数 coercion：当模型把 object / array 参数错误编码成 JSON string 时自动解码。

默认内置 agent 是薄层 profile，也是给使用者参考的标准 case；它们不是硬编码运行策略。宿主应用可以直接用，
也可以基于 `AgentSpec` 覆盖 instructions、tools、skills、model、max_steps 等字段。

默认 profile：

| 名称 | 类型 | 权限模型 | 用途 |
| --- | --- | --- | --- |
| `build` | 主 agent | read / edit / execute | 默认实施 agent，可编辑、可执行、可验证。 |
| `plan` | 主 agent | read | 只读分析 agent，用于方案、评审、拆解和风险判断。 |
| `explore` | subagent | read | 只读代码搜索 subagent，适合并行探索局部问题。 |
| `general` | subagent | read / execute | 通用多步任务 subagent，用于有边界的辅助工作。 |

代码入口：

- `DEFAULT_MAIN_AGENTS`
- `DEFAULT_SUBAGENTS`
- `get_default_agent(name)`
- `default_agent_spec(name, **overrides)`
- `default_agent_specs(role)`

相关文件：

- `src/mobmini/agents.py`
- `src/mobmini/default_agents.py`
- `src/mobmini/runtime.py`
- `src/mobmini/tools.py`

### Subagent 与 managed specialist

框架提供两层委托模式：

- `AgentRegistry` + `TaskTool`：父 agent 用 `task(agent, task, context)` 委托给子 agent。
- `ManagedSpecialistTool`：从 `dream-agent` 的 planner / writer / reviewer wrapper 抽象出的通用 specialist tool。

`ManagedSpecialistTool` 提供：

- 通过 `ContextAssembler` 构造 task body。
- normalize specialist 的 `final_answer`。
- `resume_hook`：已有产物时 short-circuit，避免重复消耗模型。
- `checkpoint_hook`：成功后由宿主应用保存结果。
- start / skip / complete / error 的结构化 metric。

它保留了 `dream-agent` 中有效的 wrapper discipline，但不绑定 DB、lease、production job state 或 checkpoint client。

相关文件：

- `src/mobmini/agents.py`
- `src/mobmini/specialists.py`
- `src/mobmini/observability.py`

### Skills

`SkillRegistry` 从包含 `SKILL.md` 的本地目录加载技能：

```text
skills/
  docs-writer/
    SKILL.md
    examples.md
```

支持：

- YAML-like frontmatter。
- skill catalog 渲染。
- `auto_load` skill 注入。
- `lookup_skill` tool。
- `lookup_skill_resource` tool。
- resource 路径逃逸保护。

相关文件：

- `src/mobmini/skills.py`

### Context assembly 与 compact

`ContextAssembler` 用代码生成每次 agent / specialist 的 task body，避免把上下文装配逻辑写散：

- text block。
- JSON block。
- priority 排序。
- pinned block。
- 简单 max-character window。

`CompactContextPolicy` 用于长上下文：

- pinned context 保留。
- 最近若干轮原样保留。
- 更旧历史生成 anchored compact prompt。
- compact 输出固定结构：Objective、Constraints、Completed Work、Current State、Important References、Open Threads、Next Steps。

相关文件：

- `src/mobmini/context.py`

### Provider 与 adapter

provider 层保持轻：

- `build_litellm_model()` 是主要入口。
- 读取 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`LLM_MODEL_FAST`。
- 对 OpenAI-compatible endpoint 自动补 `openai/<model>`。
- 默认 `tool_choice="auto"`，提高 reasoner / provider 兼容性。

`deepseek_model()` 只是 LiteLLM 上的便利 helper：处理当前 DeepSeek V4 模型名、`https://api.deepseek.com`、可选 thinking 参数和 `tool_choice="auto"`。没有引入重型 DeepSeek-specific schema 层。

Adapter：

- `mcp_tool_collection()` 包装上游 `ToolCollection.from_mcp`。
- `create_app()` 提供最小 FastAPI `/health` 和 `/run`。

相关文件：

- `src/mobmini/providers.py`
- `src/mobmini/mcp.py`
- `src/mobmini/server.py`

### Runtime utilities

通用 runtime 工具：

- `run_async()` / `set_main_loop()`：让同步 tool wrapper 安全调度宿主 event loop 上的 async 资源。
- `BoundedExecutor`：给同步执行加 timeout 边界。
- typed error hierarchy：`ProviderConfigError`、`ContextAssemblyError`、`SpecialistOutputError` 等。
- JSON-line `log_event()` / `log_metric()`。

相关文件：

- `src/mobmini/async_utils.py`
- `src/mobmini/errors.py`
- `src/mobmini/observability.py`

## 刻意不包含

当前框架不内置：

- 默认 Controller。
- 默认 JobRunner。
- checkpoint client。
- Langfuse 绑定。
- 默认 CLI 层。
- 重型 provider-specific adapter。
- `dream-agent` 的业务状态。

这些留给宿主应用或未来 optional adapter。

## 当前提交结构

`main` 在原版基线上按能力拆成原子提交：

```text
docs: rewrite Chinese project overview
feat(adapters): add litellm provider and service adapters
feat(subagents): add delegation and specialist wrappers
feat(context): add context assembler and compact policy
feat(skills): add skill registry and lookup tools
feat(runtime): add final-answer and tool utilities
chore: rename package metadata for mob mini agent
chore: import original smolagents baseline
```

## 相关页面

- [[entities/mobai-agent]]
- [[concepts/server-layer]]
- [[concepts/four-layer-philosophy]]
- [[concepts/dreaming-universe]]
