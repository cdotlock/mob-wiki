---
title: MoonShort Script (MSS) Interpreter
tags: [mss, script, interpreter, go, visual-novel]
sources: []
created: 2026-04-15
updated: 2026-04-17
---

MoonShort Script（MSS）是 MobAI 互动视觉小说的统一脚本格式及其配套解释器。一个 `.md` 脚本文件同时定义一集的叙事内容和游戏机制（D20 检定、小游戏、分支路由），Go 解释器将其编译为前端播放器可直接消费的 JSON。

仓库：[cdotlock/moonshort-script](https://github.com/cdotlock/moonshort-script)

## 产品定位

MSS 解决的核心问题是：Dramatizer 生成的剧本、Remix Executor 生成的二创内容、以及人工编写的脚本，需要一个统一的格式和工具链来编译为前端播放器的输入。

MSS 不是一个运行时引擎——它是一个编译时工具。脚本在上线前编译为 JSON，前端播放器消费 JSON，运行时不需要解释器。

## 架构

解释器是一个 Go 单二进制工具 `mss`，内部有 6 个模块，按管线顺序执行：

```
.md 脚本 → Lexer → Parser → Validator → Fixer(可选) → Resolver → Emitter → JSON
```

### 模块职责

| 模块 | 路径 | 职责 |
|------|------|------|
| Token | `internal/token/` | 定义 token 类型（AT、AMPERSAND、IDENT、STRING、NUMBER、操作符等） |
| Lexer | `internal/lexer/` | 将原始文本拆分为 token 流。处理 `@`/`&` 前缀、`{ }` 块界定、`"..."` 字符串、`//` 注释、`>=` `&&` 等操作符。特殊方法 `ReadDialogueText()` 读取对话行冒号后的全部文本 |
| AST | `internal/ast/` | 定义 25+ 种 AST 节点类型。所有 body 级节点内嵌 `ConcurrentFlag` 标记 `&` 并发前缀。条件为**完全结构化 AST**：`Condition` 是 interface，具体类型包括 `ChoiceCondition` / `FlagCondition` / `InfluenceCondition` / `ComparisonCondition` / `CompoundCondition`。终结标记 `EndingNode` 挂在 `Episode.Ending` 字段（与 `Episode.Gate` 互斥） |
| Parser | `internal/parser/` | 递归下降解析器，将 token 流组装为 AST。关键设计：通过排除法识别角色指令——`@`/`&` 后的 IDENT 如果不是已知关键字，就视为角色名。条件解析为结构化 AST，采用 `||` < `&&` < primary 优先级的递归下降表达式解析器。支持 `@else @if` 链式条件、嵌套括号、递归深度限制（50 层） |
| Validator | `internal/validator/` | 对 AST 做语义校验：每集必须有 `@gate` 或 `@ending`（二者互斥）、`@ending` 类型白名单（complete/to_be_continued/bad_ending）、brave 选项必须有 check + @on success/fail、safe 选项不能有 check、`@goto` 必须有匹配的 `@label`、选项 ID 不能重复、position/transition/bubble_type/option_mode 白名单校验、条件 AST 结构校验（op 白名单、operand 非空） |
| Fixer | `internal/fixer/` | 文本级自动修复（仅通过 `mss fix` 显式调用）：BOM/CRLF 规范化、`&` 块结构→`@`、`@if` 补括号、`@check`→`check`、角色名大小写统一、`@butterfly` 补引号、补缺失 `}`、旧格式检测（13 种废弃关键字） |
| Resolver | `internal/resolver/` | 读取独立的 JSON 素材映射表，将脚本中的语义名翻译为完整 OSS URL |
| Emitter | `internal/emitter/` | 将 AST 转为前端可消费的 JSON。并发节点（`&` 标记）自动分组为数组，单步为对象。Gate 输出嵌套 if/else 链。条件输出半结构化对象（带 type 字段） |

### 关键设计决策

**`@`/`&` 并发模型**：`@` 开始新步骤组（顺序），`&` 加入上一个步骤组（并发）。对话始终独立。JSON 输出中，并发组为数组，单步为对象，引擎按顺序遍历 steps 数组即可。

**结构化条件 AST**：条件不是字符串，也不只是带 type 的半结构化对象——**所有 5 种条件类型都解析为完全结构化的 AST**。comparison 的 `left` 拆为 `{kind, char/name}`，`right` 为整数；compound 的 `left`/`right` 是递归条件对象。后端消费 JSON 时直接遍历 AST，无需再次解析表达式字符串。

**嵌套 if/else gate**：Gate 路由从扁平数组改为嵌套 if/else 链，与 body `@if` 结构一致，引擎只需一套递归逻辑处理两种场景。

**集终结二元设计**：每集必须以 `@gate { ... }`（路由）或 `@ending <type>`（终结）之一结尾，不可同时出现。`@ending` 三种类型：`complete`（全剧终）、`to_be_continued`（待续）、`bad_ending`（坏结局）。JSON 输出的 `gate` 和 `ending` 两字段**恒存在**，未使用的一方为 `null`——前端可以确定性判别。

**脚本与素材分离**：脚本只写语义名，不包含任何 URL。素材映射是独立的 JSON 文件，通过 `--assets` 参数读入。同一套脚本可以指向不同 OSS 环境。

**fix 只在显式调用时执行**：`mss compile` 和 `mss validate` 遇到问题直接报错，不会自动修复。只有 `mss fix` 才会修改文件。

## 命令行用法

```bash
# 编译单集脚本为 JSON
mss compile episode.md --assets mapping.json -o output.json

# 批量编译整个目录
mss compile novel_001/ --assets mapping.json -o novel.json

# 验证脚本语法（不输出 JSON）
mss validate episode.md

# 自动修复常见语法错误
mss fix episode.md -o fixed.md
```

## JSON 输出结构

编译后的 JSON 是前端播放器的直接输入，设计原则是**类型明确、URL 已解析、并发已分组**：

```json
{
  "episode_id": "main:01",
  "branch_key": "main",
  "seq": 1,
  "title": "Butterfly",
  "steps": [
    [
      {"type": "bg", "name": "classroom", "url": "https://...", "transition": "fade"},
      {"type": "music_play", "name": "calm", "url": "https://..."},
      {"type": "char_show", "character": "malia", "look": "neutral", "position": "left", "url": "https://..."}
    ],
    {"type": "narrator", "text": "Senior year. Day one."},
    {"type": "dialogue", "character": "josie", "text": "MALIA!"},
    {"type": "choice", "options": [
      {"id": "A", "mode": "brave", "text": "Stand your ground.",
       "check": {"attr": "CHA", "dc": 12}, "on_success": [...], "on_fail": [...]},
      {"id": "B", "mode": "safe", "text": "Walk away.", "steps": [...]}
    ]}
  ],
  "gate": {
    "if": {"type": "choice", "option": "A", "result": "fail"},
    "next": "main/bad/001:01",
    "else": {
      "if": {"type": "influence", "description": "Player showed empathy"},
      "next": "main/route/001:01",
      "else": {"next": "main:02"}
    }
  },
  "ending": null
}
```

终结集示例：

```json
{
  "episode_id": "main/bad/001:02",
  "branch_key": "main/bad/001",
  "seq": 2,
  "title": "Bad End",
  "steps": [
    {"type": "narrator", "text": "She never came home."}
  ],
  "gate": null,
  "ending": {"type": "bad_ending"}
}
```

`steps` 是混合类型数组：对象 = 单步，数组 = 并发组。`gate` 和 `ending` 两字段恒存在且互斥：路由集 `ending: null`，终结集 `gate: null`。比较/复合条件全部输出结构化 AST（无 `expr` 字段）。character 字段始终小写。

## 测试覆盖

经过两轮完整审计，测试覆盖率：parser 81.6%, lexer 86.4%, resolver 90.3%, emitter 93.7%, fixer 98.0%, validator 98.9%。包含 200+ 测试用例、黄金文件集成测试、136 个边界条件测试。

## 与其他系统的关系

**[[entities/dramatizer]]**：Dramatizer 的 Phase 3（ludify 阶段）将重构为输出 MSS 格式。

**[[entities/agent-forge]]**：Agent-Forge 的视频工作流将转型为 VN 素材管线，负责生成背景、角色立绘、CG 等素材，并维护素材映射表。

**Remix Executor**：后端 Remix 管线的 Executor 阶段将输出 MSS 格式，与 Dramatizer 产出完全一致。

**前端播放器**：消费 MSS 解释器输出的 JSON，渲染互动视觉小说体验。播放器不需要理解 MSS 脚本——它只消费 JSON。

## Agent Skill

项目内置了 `skills/mss-scriptwriting/` 目录，包含完整的 Agent Skill，教 LLM 如何正确生成 MSS 脚本。覆盖完整语法规则、17 条常见错误、`@ending` 终结指令、结构化条件语法、Remix 差异点、节奏指导、fixer 自动修复能力。Dramatizer 和 Remix Executor 的 LLM 在生成脚本时应加载此 Skill。

详细格式规范见 [[concepts/mss-format]]。
