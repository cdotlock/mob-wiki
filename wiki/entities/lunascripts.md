---
title: Lunascripts (LS) Interpreter
tags: [ls, script, interpreter, go, visual-novel, fastapi]
sources: []
created: 2026-04-15
updated: 2026-05-30
---

Lunascripts（LS）是 MobAI 互动视觉小说的统一脚本格式及其配套解释器。一个 `.md` 脚本文件同时定义一集的叙事内容和游戏机制（D20 检定、小游戏、分支路由），Go 解释器将其编译为前端播放器可直接消费的 JSON。

仓库：[cdotlock/lunascripts](https://github.com/cdotlock/lunascripts)

## 2026-05 关键改动

- **`@trick` 与 `@minigame` 彻底解耦**（`56a0c5d`）— 历史上 `@minigame` 块体内能写 `@if (rating.X) { }` 分叉、还能内嵌 trick；现在两者是平级的叶子原语，`@minigame` 退化成 prose-driven 叶子步（无 body、无 rating 分支）。剧情围绕 minigame 结果分叉的，请在 minigame 后用 `@if` 读引擎给的 signal int / butterfly，而不是 minigame body 内嵌 rating。
- **trick 白名单锁死 6 类**（`b32da17` lock + `2630189` stress reduce + `370e10e` 把 hold-still 换成 tilt）— `hold` / `tap` / `swipe` / `shake` / `swing` / `tilt`。原 hold-still 被剔（与 hold 信号源重叠 + 检测玩家默认姿态，不构成 trick）；同时不收摄像头 / 麦克风模态（运行时权限墙太重、拒绝即卡死玩家）。**backwards-compat 代码全删**（不再支持别名 / 旧字符串）。
- **spec 不再描述迁移路径**（`a5b0135`）— `LS-SPEC.md` 整体改写按当前模型描述，旧的 "migration notes" 删干净，新读者不需要先理解历史。详见 [`LS-SPEC.md`](https://github.com/cdotlock/lunascripts/blob/main/LS-SPEC.md) + [`README.md`](https://github.com/cdotlock/lunascripts/blob/main/README.md) 同步刷新。
- **episode-scoped step ID 编号**（`79e3e8d` → `4699476` 同步漏修）— stable step ID 编号从 container-scoped（一个 `@choice` 内 reset）改成 episode-scoped（一集内全局递增），简化跨集的 cursor 寻址。详见 [[concepts/stable-step-id]]。
- **FastAPI HTTP wrapper**（`e133bf4` + `d42570c` 补 validate/fix/compile-dir + `cdbe49ce` 写完整 FASTAPI.md）— 新增 `cmd/server` (FastAPI Python wrapper) 暴露 CLI 全功能为 HTTP endpoint，LLM 可自助调用：`POST /compile` / `POST /validate` / `POST /fix` / `POST /compile-dir` / `GET /` 根列表。已部署 stable public URL（Mob Sandbox Daytona），详见 [`FASTAPI.md`](https://github.com/cdotlock/lunascripts/blob/main/FASTAPI.md)。本仓 Go binary 仍可直跑，FastAPI 是给跨语言客户端 + LLM agent 用的。

## 产品定位

LS 解决的核心问题是：Dramatizer 生成的剧本、Remix Executor 生成的二创内容、以及人工编写的脚本，需要一个统一的格式和工具链来编译为前端播放器的输入。

LS 不是一个运行时引擎——它是一个编译时工具。脚本在上线前编译为 JSON，前端播放器消费 JSON，运行时不需要解释器。

## 架构

解释器是一个 Go 单二进制工具 `ls`，内部有 6 个模块，按管线顺序执行：

```
.md 脚本 → Lexer → Parser → Validator → Fixer(可选) → Resolver → Emitter → JSON
```

### 模块职责

| 模块 | 路径 | 职责 |
|------|------|------|
| Token | `internal/token/` | 定义 token 类型（AT、AMPERSAND、IDENT、STRING、NUMBER、操作符等） |
| Lexer | `internal/lexer/` | 将原始文本拆分为 token 流。处理 `@`/`&` 前缀、`{ }` 块界定、`"..."` 字符串、`//` 注释、`>=` `&&` 等操作符。特殊方法 `ReadDialogueText()` 读取对话行冒号后的全部文本 |
| AST | `internal/ast/` | 定义 25+ 种 AST 节点类型。所有 body 级节点内嵌 `ConcurrentFlag` 标记 `&` 并发前缀。条件为**完全结构化 AST**：`Condition` 是 interface，具体类型包括 `ChoiceCondition` / `FlagCondition` / `InfluenceCondition` / `ComparisonCondition` / `CompoundCondition` / `CheckCondition`（brave option 体内合法）。终结标记 `EndingNode` 挂在 `Episode.Ending` 字段（与 `Episode.Gate` 互斥）。`SignalNode` 带 `Kind` 字段（当前只认 `mark`，字段保留用于未来扩展）。`AchievementNode` 是 inline body step，块内携带 `ID` / `Name` / `Rarity` / `Description`——既是元数据也是触发点。`MinigameNode` 是**叶子节点**（无 body；含 `Description` 必填）；`TrickNode` 同样叶子（含 `Type` + `Prompt`，type 锁 6 类）；`OptionNode` 只有 `Body []Node`；`CgShowNode` 含 `Duration` + `Content` 必填字段 |
| Parser | `internal/parser/` | 递归下降解析器，将 token 流组装为 AST。关键设计：通过排除法识别角色指令——`@`/`&` 后的 IDENT 如果不是已知关键字，就视为角色名。条件解析为结构化 AST，采用 `||` < `&&` < primary 优先级的递归下降表达式解析器。支持 `@else @if` 链式条件、嵌套括号、递归深度限制（50 层）。`@on` 不属于语法，parser 见到会直接报错并给出迁移提示；`@achievement <id>` 必须跟 `{ ... }` 块（裸形式是 parse error）；`@cg` 和 `@minigame` 解析时强制读取必填字段 |
| Validator | `internal/validator/` | 对 AST 做语义校验：每集必须有 `@gate` 或 `@ending`（二者互斥）、`@ending` 类型白名单（complete/to_be_continued/bad_ending）、`@signal` kind 白名单（当前仅 mark）、`@achievement` 字段完整性 + rarity 白名单（uncommon/rare/epic/legendary，禁 common）、brave 选项必须有 check（不强制 `@if (check.success)` 分支完备，允许作者省略 else）、safe 选项不能有 check、`@goto` 必须有匹配的 `@label`、选项 ID 不能重复、position/transition/bubble_type/option_mode 白名单校验、条件 AST 结构校验（op 白名单、operand 非空、check.result 白名单）、CG duration 白名单（low/medium/high）+ content 非空、minigame description 非空、**trick type 锁 6 类**（hold/tap/swipe/shake/swing/tilt） |
| Fixer | `internal/fixer/` | 文本级自动修复（仅通过 `lsc fix` 显式调用）：BOM/CRLF 规范化、`&` 块结构→`@`、`@if` 补括号、`@check`→`check`、角色名大小写统一、`@butterfly` 补引号、补缺失 `}`、旧格式检测（13 种废弃关键字） |
| Resolver | `internal/resolver/` | 读取独立的 JSON 素材映射表，将脚本中的语义名翻译为完整 OSS URL |
| Emitter | `internal/emitter/` | 将 AST 转为前端可消费的 JSON。并发节点（`&` 标记）自动分组为数组，单步为对象。Gate 输出嵌套 if/else 链。条件输出半结构化对象（带 type 字段） |

### 关键设计决策

**`@`/`&` 并发模型**：`@` 开始新步骤组（顺序），`&` 加入上一个步骤组（并发）。对话始终独立。JSON 输出中，并发组为数组，单步为对象，引擎按顺序遍历 steps 数组即可。

**结构化条件 AST**：条件不是字符串，也不只是带 type 的半结构化对象——**所有 5 种条件类型都解析为完全结构化的 AST**。comparison 的 `left` 拆为 `{kind, char/name}`，`right` 为整数；compound 的 `left`/`right` 是递归条件对象。后端消费 JSON 时直接遍历 AST，无需再次解析表达式字符串。

**嵌套 if/else gate**：Gate 路由从扁平数组改为嵌套 if/else 链，与 body `@if` 结构一致，引擎只需一套递归逻辑处理两种场景。

**集终结二元设计**：每集必须以 `@gate { ... }`（路由）或 `@ending <type>`（终结）之一结尾，不可同时出现。`@ending` 三种类型：`complete`（全剧终）、`to_be_continued`（待续）、`bad_ending`（坏结局）。JSON 输出的 `gate` 和 `ending` 两字段**恒存在**，未使用的一方为 `null`——前端可以确定性判别。

**Signal 单 kind + 成就 inline 触发**：`@signal <kind> <event>` 语法保留 kind 词元，当前只实现 `mark`——持久布尔标记，可被 `@if (NAME)` 查询。成就由独立的 `@achievement <id> { name / rarity / description }` 指令承担——块既是元数据也是触发点，执行到该节点即解锁。条件触发由外层 `@if` 控制：`@if (mark1 && mark2) { @achievement X { ... } }`。引擎侧被动响应 `{"type":"achievement","id":X,"name":...,"rarity":...,"description":...}` step（step 自带完整元数据），按 id 去重，无需单独的声明表或 watcher。

**CG 视频字段**：`@cg show` 块必须在 body 节点之前声明 `duration:` 和 `content:` 两个字段。`duration` 是档位（`low` / `medium` / `high`），`content` 是英文连续叙述（镜头走向 + 情节）。这两个字段供 agent-forge 视频管线消费——LS 是流程控制 + 内容，剧本必须带镜头描述，否则下游没法生成 CG 视频。

**Context-local 条件**：`check.success` / `check.fail` 只在 brave option 体内合法。brave option 的 outcome 分支走 `@if (check.success) { } @else { }`，JSON 输出为 `{"type":"check","result":"..."}`。编译器**不**做作用域静态校验（作用域错放运行时恒为 false，视为作者的剧情 bug）。

> **2026-05 起 `RatingCondition` / `@if (rating.X)` 不再被支持** — `@minigame` 已退化为 prose 叶子步、无 body、不参与 D20。需要按 minigame 结果分叉的剧情，请在 `@minigame` 后用 `@if (signal_int >= N)` / `@if (FLAG_NAME)` / `@if ("influence ...")` 等读引擎写回的 signal / butterfly。

**Minigame description**：`@minigame <name> "<description>"` 叶子语法。`<name>` 是素材句柄，下游 vibe-coding agent 按描述生成 minigame 包，URL 落 `assets.minigames.<name>`；description 是给生成 agent 的 prose 输入。`@minigame` 不绑定属性、不影响 D20——奖励完全在引擎侧（反作弊），脚本一个数字都不写。XP / SAN / reroll / coins / gems 等数值经济由引擎管理；脚本只能在 `@if` 里读引擎管理的数值。2026-05 前的 `@minigame <id> <ATTR> "<desc>" { @if (rating.X) ... }` 块体语法**已删**，无 backwards-compat。

**脚本与素材分离**：脚本只写语义名，不包含任何 URL。素材映射是独立的 JSON 文件，通过 `--assets` 参数读入。同一套脚本可以指向不同 OSS 环境。

**fix 只在显式调用时执行**：`lsc compile` 和 `lsc validate` 遇到问题直接报错，不会自动修复。只有 `lsc fix` 才会修改文件。

## 命令行用法

```bash
# 编译单集脚本为 JSON
lsc compile episode.md --assets mapping.json -o output.json

# 批量编译整个目录
lsc compile novel_001/ --assets mapping.json -o novel.json

# 验证脚本语法（不输出 JSON）
lsc validate episode.md

# 自动修复常见语法错误
lsc fix episode.md -o fixed.md
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
       "check": {"attr": "CHA", "dc": 12},
       "steps": [
         {"type": "if",
          "condition": {"type": "check", "result": "success"},
          "then": [...], "else": [...]}
       ]},
      {"id": "B", "mode": "safe", "text": "Walk away.", "steps": [...]}
    ]},
    {"type": "achievement", "id": "HEEL_WARRIOR",
     "name": "Heel as Weapon", "rarity": "rare",
     "description": "You turned an accessory into a warning."}
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

**[[entities/dramatizer]]**：Dramatizer 的 Phase 3（ludify 阶段）将重构为输出 LS 格式。

**[[entities/agent-forge]]**：Agent-Forge 的视频工作流将转型为 VN 素材管线，负责生成背景、角色立绘、CG 等素材，并维护素材映射表。

**Remix Executor**：后端 Remix 管线的 Executor 阶段将输出 LS 格式，与 Dramatizer 产出完全一致。

**前端播放器**：消费 LS 解释器输出的 JSON，渲染互动视觉小说体验。播放器不需要理解 LS 脚本——它只消费 JSON。

## Agent Skill

项目内置了 `skills/ls-scriptwriting/` 目录，包含完整的 Agent Skill，教 LLM 如何正确生成 LS 脚本。覆盖完整语法规则、常见错误清单、`@ending` 终结指令、结构化条件语法（含 context-local `check`/`rating`）、CG `duration` + `content`、minigame description、Remix 差异点、节奏指导、fixer 自动修复能力。Dramatizer 和 Remix Executor 的 LLM 在生成脚本时应加载此 Skill。

## 引擎集成

运行时消费 LS JSON 的引擎（前端播放器 / 后端数据管线）参考 [`docs/ENGINE-INTEGRATION.md`](https://github.com/cdotlock/lunascripts/blob/main/docs/ENGINE-INTEGRATION.md)——覆盖 step 遍历规则、signal kind 向前兼容、achievement step 消费、context-local check/rating 求值、CG duration/content 字段用途以及条件求值伪代码。

详细格式规范见 [[concepts/ls-format]]。
