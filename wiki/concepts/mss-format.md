---
title: MoonShort Script (MSS) 格式规范
tags: [mss, script-format, visual-novel, specification]
sources: []
created: 2026-04-15
updated: 2026-04-20
---

MoonShort Script（MSS）是 MobAI 互动视觉小说的脚本标记语言。一个 `.md` 文件描述一集的全部内容——场景、角色、对话、音频、D20 检定、小游戏、分支路由——由 Go 解释器编译为 JSON 供前端播放器消费。

解释器实体信息见 [[entities/moonshort-script]]。

## 设计原则

1. **单一格式统一叙事与游戏机制**：不分剧本文件和数据文件，一个文件搞定一切
2. **自包含**：每个文件包含一集所需的全部信息，不依赖外部清单
3. **LLM 友好**：由 Dramatizer 和 Remix Executor（LLM 管线）生成，语法对 LLM 自然
4. **素材解耦**：脚本只写语义名，解释器通过独立映射表翻译为 OSS URL
5. **并发分组**：`@`/`&` 前缀让编译器自动生成并发执行组，引擎无需猜测时序

## 三种语法

MSS 文件内交替使用三种语法：

**1. 顺序指令 `@`**：每个 `@` 开始一个新的执行步骤。
```
@bg set school_hallway fade
@mauricio show neutral_smirk at right
```

**2. 并发指令 `&`**：加入前一个 `@` 的步骤组，同时执行。
```
@bg set school_hallway fade          // 新步骤组
&music crossfade tense_strings       // 并发
&mauricio show neutral_smirk at right // 并发
```

**3. 对话行**：角色名大写 + 冒号，始终独立步骤。
```
MAURICIO: Hey, Butterfly.
NARRATOR: Senior year. Day one.
YOU: He hasn't called me that in eight years.
```

语法糖：`CHARACTER [look]: text` = 换表情 + 对话合写。

## 完整指令表

### 结构
| 指令 | 说明 |
|------|------|
| `@episode <key> "<title>" { }` | 集定义（根块） |
| `@gate { }` | 路由声明（集尾部，与 `@ending` 二选一） |
| `@ending <type>` | 终结标记（`complete` / `to_be_continued` / `bad_ending`，与 `@gate` 二选一） |
| `@if (<condition>): @next <target>` | Gate 条件路由 |
| `@else @if (<condition>): @next <target>` | Gate 链式条件 |
| `@else: @next <target>` | Gate 兜底路线 |
| `@label <name>` / `@goto <name>` | 集内跳转（慎用） |
| `@pause for N` | 等待 N 次点击 |

**终结规则**：每集必须以 `@gate` 或 `@ending` 二者之一结尾。两者互斥——有 gate 表示继续路由，有 ending 表示全剧终/待续/坏结局。既无 gate 也无 ending 在 validator 阶段报 `MISSING_TERMINAL`。

### 视觉
| 指令 | 说明 |
|------|------|
| `@<char> show <look> at <pos> [trans]` | 角色入场 |
| `@<char> hide [trans]` | 角色退场 |
| `@<char> look <look> [trans]` | 换表情 |
| `@<char> move to <pos>` | 角色移位 |
| `@<char> bubble <type>` | 气泡动画 |
| `@bg set <name> [trans]` | 切背景 |
| `@cg show <name> [trans] { duration: ... content: "..." ... }` | CG 展示块，`duration` + `content` 必填 |

**位置**：`left` `center` `right` `left_far` `right_far`
**过渡**：`fade` `cut` `slow` `dissolve`（不写 = 默认）
**气泡**：`anger` `sweat` `heart` `question` `exclaim` `idea` `music` `doom` `ellipsis`

**CG 字段（必填）**：CG 下游由 agent-forge 渲染为短视频，script 必须带镜头 + 情节描述：

- `duration:` — 档位 `low` / `medium` / `high`（不写秒数）
- `content:` — 英文连续叙述，讲清楚镜头怎么走、画面强调什么
- 字段之后是 body 节点（对白/叙事等），CG 放映期间播放

### 对话
| 语法 | 说明 |
|------|------|
| `CHARACTER: text` | 角色对白 |
| `CHARACTER [look]: text` | 对白 + 换表情 |
| `NARRATOR: text` | 旁白 |
| `YOU: text` | 内心独白 |

### 音频
| 指令 | 说明 |
|------|------|
| `@music play <name>` | 播放 BGM |
| `@music crossfade <name>` | 交叉淡入 |
| `@music fadeout` | 淡出停止 |
| `@sfx play <name>` | 音效 |

### 手机
| 指令 | 说明 |
|------|------|
| `@phone show { }` / `@phone hide` | 手机界面 |
| `@text from/to <char>: content` | 短信 |

### 游戏机制
| 指令 | 说明 |
|------|------|
| `@minigame <id> <ATTR> "<description>" { }` | 小游戏（description 必填；body 用 `@if (rating.X)` 分支） |
| `@choice { @option ... }` | 选择块 |
| `@option <ID> brave "<text>" { check {} @if (check.success) {} @else {} }` | 勇敢选项（check 分支用 `@if (check.success)` 树） |
| `@option <ID> safe "<text>" { }` | 安全选项 |

- brave option 的成功/失败分支用 `@if (check.success) { } @else { }`；minigame 的评级分支用 `@if (rating.<grade>) { } @else @if (...) { }`
- `check.success` / `check.fail` 是 brave option 体内合法的 context-local 条件，`rating.<grade>` 是 minigame 体内合法
- `@minigame` 第三位参数是英文短描述（必填），给下游视觉管线用

### 状态变更
| 指令 | 说明 |
|------|------|
| `@affection <char> +/-N` | 好感度 |
| `@signal <kind> <event>` | 事件信号。当前仅 `kind=mark` 实现（持久布尔标记，可被 `@if (NAME)` 查询）。kind 词元保留以便未来扩展 |
| `@butterfly "<desc>"` | 蝴蝶效应记录 |
| `@achievement <id> { name / rarity / description }` | 成就解锁（块内携带完整元数据，执行到该节点就是解锁时机） |

**Signal kind**：`@signal <kind> <event>` 语法中 kind 必写。当前只实现 `mark`——用于持久布尔标记，通过 `@if (NAME)` 查询。JSON 输出中每个 signal 步骤都带 `"kind":"mark"` 字段；未知 kind 引擎应向前兼容（忽略 + 日志）。

**Achievement**：一条指令、一种形态——`@achievement <id> { ... }` 块既是元数据也是触发点。条件触发用外层 `@if` 包：

```
@if (HIGH_HEEL_EP05 && HIGH_HEEL_EP24) {
  @achievement HIGH_HEEL_DOUBLE_KILL {
    name: "Heel Twice Over"
    rarity: epic
    description: "Once is improvisation. Twice is a signature move."
  }
}
```

- `rarity` 必须为 `uncommon` / `rare` / `epic` / `legendary`——**禁用 `common`**
- 三个字段 `name` / `rarity` / `description` 都必填；裸 `@achievement <id>` 无块是 parse error
- 同一 id 从多个剧情点触发是合法的——引擎按 id 在 unlock 时去重
- JSON 输出形态：`{"type":"achievement","id":"...","name":"...","rarity":"...","description":"..."}`（step 自带元数据，JSON 顶层**不**再有独立的 `achievements` 数组）

### 流程控制
```
@if (affection.easton >= 5) {
  EASTON: You remembered.
} @else @if (CHA >= 14) {
  EASTON: Interesting.
} @else {
  EASTON: ...Hey.
}
```

**条件类型（共 7 种，全部编译为结构化 AST——后端消费 JSON 时直接遍历，无需再次解析表达式字符串）**：

| 类型 | 语法 | AST 输出 | 作用域 |
|------|------|--------|-------|
| flag | `SIGNAL_NAME` | `{type:"flag", name}` | 任意 |
| comparison | `affection.<char> op N` / `<name> op N` | `{type:"comparison", left:{kind,char/name}, op, right}` | 任意 |
| compound | `<expr> && <expr>` / `<expr> \|\| <expr>` | `{type:"compound", op, left, right}`（递归嵌套） | 任意 |
| choice | `OPTION.result` | `{type:"choice", option, result}` — result: success/fail/any | 任意（回顾性） |
| influence | `influence "desc"` 或 `"desc"` | `{type:"influence", description}` | 任意 |
| check | `check.success` / `check.fail` | `{type:"check", result}` | **仅 brave option 体内** |
| rating | `rating.<grade>` | `{type:"rating", grade}` | **仅 `@minigame` 体内** |

比较右侧必须是整数字面量。`left.kind` 为 `"affection"`（附带 `char`）或 `"value"`（附带 `name`）。复合条件的 `left`/`right` 是递归条件对象，不是字符串。

**check vs choice 区别**：`check.success` 回答"当前这个 brave option 的检定成了吗"（context-local），`A.success` 回答"玩家在选项 A 上历史上选过且成了吗"（回顾性）。两者在 JSON AST 里是完全不同的类型。

**context-local 作用域**：`check` / `rating` 条件只在各自作用域内有效；作用域外求值运行时恒为 false（不是语法错）——作者写错位置是剧情 bug，validator 不做检查。

## Gate 路由

```
@gate {
  @if (A.fail): @next main/bad/001:01
  @else @if (influence "Player showed empathy"): @next main/route/001:01
  @else: @next main:02
}
```

Gate 必须位于 `@episode` 块尾部。所有 5 种条件类型均可在 gate 中使用。JSON 输出为嵌套 if/else 链，条件字段为完全结构化 AST。

## Ending 终结

```
@episode main/bad/001:02 "Bad End" {
  NARRATOR: She never came home.
  @ending bad_ending
}
```

三种 ending 类型：

| type | 含义 |
|------|------|
| `complete` | 全剧终（主线大结局、所有 Happy End） |
| `to_be_continued` | 待续（本章/本季完，下一章未写） |
| `bad_ending` | 坏结局（玩家失败、角色死亡、关系破裂） |

JSON 输出中 `ending` 与 `gate` 字段恒存在，终结集 `gate: null`，路由集 `ending: null`。

## 命名与寻址

文件路径即 episode_id：`novel_<id>/main/01.md` → `main:01`，`novel_<id>/main/bad/001/01.md` → `main/bad/001:01`。

## Remix 兼容

Remix 脚本格式完全一致，branch_key 使用 `remix/<session_id>:01`。通过 gate 的 `@else: @next main:02` 回归主线。

## 引擎不可修改的值

XP、SAN/HP 等数值由游戏引擎内部管理，脚本不能修改，只能在 `@if` 条件中读取（如 `@if (san <= 20) { }`）。
