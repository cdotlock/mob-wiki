---
title: MoonShort Script (MSS) 格式规范
tags: [mss, script-format, visual-novel, specification]
sources: []
created: 2026-04-15
updated: 2026-04-16
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
| `@gate { }` | 路由声明（集尾部，必须有） |
| `@if (<condition>): @next <target>` | Gate 条件路由 |
| `@else @if (<condition>): @next <target>` | Gate 链式条件 |
| `@else: @next <target>` | Gate 兜底路线 |
| `@label <name>` / `@goto <name>` | 集内跳转（慎用） |
| `@pause for N` | 等待 N 次点击 |

### 视觉
| 指令 | 说明 |
|------|------|
| `@<char> show <look> at <pos> [trans]` | 角色入场 |
| `@<char> hide [trans]` | 角色退场 |
| `@<char> look <look> [trans]` | 换表情 |
| `@<char> move to <pos>` | 角色移位 |
| `@<char> bubble <type>` | 气泡动画 |
| `@bg set <name> [trans]` | 切背景 |
| `@cg show <name> [trans] { }` | CG 展示块 |

**位置**：`left` `center` `right` `left_far` `right_far`
**过渡**：`fade` `cut` `slow` `dissolve`（不写 = 默认）
**气泡**：`anger` `sweat` `heart` `question` `exclaim` `idea` `music` `doom` `ellipsis`

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
| `@minigame <id> <ATTR> { @on <ratings> { } }` | 小游戏 |
| `@choice { @option ... }` | 选择块 |
| `@option <ID> brave "<text>" { check {} @on success {} @on fail {} }` | 勇敢选项 |
| `@option <ID> safe "<text>" { }` | 安全选项 |

### 状态变更
| 指令 | 说明 |
|------|------|
| `@affection <char> +/-N` | 好感度 |
| `@signal <event>` | 事件 + 持久布尔标记 |
| `@butterfly "<desc>"` | 蝴蝶效应记录 |

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

**条件类型（5 种）**：

| 类型 | 语法 | 示例 |
|------|------|------|
| flag | `SIGNAL_NAME` | `@if (EP01_COMPLETE) { }` |
| comparison | `value op number` | `@if (affection.easton >= 5) { }` |
| compound | `expr && expr` | `@if (san <= 20 \|\| FAILED_TWICE) { }` |
| choice | `OPTION.result` | `@if (A.fail) { }` — result: success/fail/any |
| influence | `influence "desc"` 或 `"desc"` | `@if (influence "player showed empathy") { }` |

## Gate 路由

```
@gate {
  @if (A.fail): @next main/bad/001:01
  @else @if (influence "Player showed empathy"): @next main/route/001:01
  @else: @next main:02
}
```

Gate 必须位于 `@episode` 块尾部。所有 5 种条件类型均可在 gate 中使用。JSON 输出为嵌套 if/else 链。

## 命名与寻址

文件路径即 episode_id：`novel_<id>/main/01.md` → `main:01`，`novel_<id>/main/bad/001/01.md` → `main/bad/001:01`。

## Remix 兼容

Remix 脚本格式完全一致，branch_key 使用 `remix/<session_id>:01`。通过 gate 的 `@else: @next main:02` 回归主线。

## 引擎不可修改的值

XP、SAN/HP 等数值由游戏引擎内部管理，脚本不能修改，只能在 `@if` 条件中读取（如 `@if (san <= 20) { }`）。
