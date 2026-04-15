---
title: MoonShort Script (MSS) 格式规范
tags: [mss, script-format, visual-novel, specification]
sources: []
created: 2026-04-15
updated: 2026-04-15
---

MoonShort Script（MSS）是 MobAI 互动视觉小说的脚本标记语言。一个 `.md` 文件描述一集的全部内容——场景、角色、对话、音频、D20 检定、小游戏、分支路由——由 Go 解释器编译为 JSON 供前端播放器消费。本文定义完整的语法规则。

解释器实体信息见 [[entities/moonshort-script]]。

## 设计原则

1. **单一格式统一叙事与游戏机制**：不分剧本文件和数据文件，一个文件搞定一切
2. **自包含**：每个文件包含一集所需的全部信息，不依赖外部清单
3. **LLM 友好**：由 Dramatizer 和 Remix Executor（LLM 管线）生成，语法对 LLM 自然
4. **素材解耦**：脚本只写语义名，解释器通过独立映射表翻译为 OSS URL

## 文件结构

### 粒度与后缀

一个 `.md` 文件 = 一集。使用 `.md` 后缀以便随处打开和 GitHub 预览。

### 命名与寻址

文件路径即 episode_id。目录结构是 `branch_key`，文件名（不含扩展名）是 `seq`：

```
novel_<id>/
├── main/
│   ├── 01.md                      # main:01
│   ├── 02.md                      # main:02
│   ├── bad/001/01.md              # main/bad/001:01
│   ├── route/001/01.md            # main/route/001:01
│   └── minor/11_a/01.md           # main/minor/11_a:01
└── remix/<session_id>/01.md       # remix/<session_id>:01
```

## 语法基础

```
// 注释：行首 //
// 空行被忽略

@episode main:01 "Bad Idea" {
  // 所有内容在 @episode 块内
  // 指令以 @ 开头：@<对象> <行动> [参数]
  // 对话以角色名大写开头：CHARACTER: text
  // 块用 { } 界定，支持嵌套
}
```

## 完整指令定义

### 结构控制

**`@episode <branch_key> "<title>" { }`** — 集定义，整个文件的根块。

**`@gates { }`** — 路由声明块，必须位于 `@episode` 块的尾部。引擎按声明顺序从上到下判定 `@gate`，第一个命中生效；全不命中走 `@default`。

```
@gates {
  @gate main/bad/001:01 {
    type: choice
    trigger: A fail
  }
  @gate main/route/001:01 {
    type: influence
    condition: "玩家展现过对Easton的持续接纳"
  }
  @default main:02
}
```

**`@gate <branch_key> { }`** — 跳转规则，两种类型：

| 类型 | 字段 | 说明 |
|------|------|------|
| `choice` | `trigger: <option_id> <result>` | 根据玩家选择跳转。result: `success` / `fail` / `any` |
| `influence` | `condition: "<描述>"` | LLM 读取累积的 `@butterfly` 记录判断是否满足条件 |

**`@default <branch_key>`** — 兜底路线，必须存在。

**`@label <name>` / `@goto <name>`** — 集内跳转锚点，高级指令，尽可能不使用。

### 视觉呈现

所有视觉指令遵循**对象-行动**模式。

#### 角色

```
@mauricio show neutral_smirk at right     // 入场
@mauricio hide fade                        // 退场（带淡出）
@mauricio expr arms_crossed_angry          // 换表情（瞬切）
@mauricio expr arms_crossed dissolve       // 换表情（交叉溶解）
@mauricio move to left                     // 滑动到新位置
@mauricio bubble heart                     // 气泡动画（自动消失）
```

**位置参数**：`left` | `center` | `right` | `left_far` | `right_far`

**气泡类型**：`anger` | `sweat` | `heart` | `question` | `exclaim` | `idea` | `music` | `doom` | `ellipsis`

**过渡效果**（用于 hide、expr）：不写 = 瞬切，`fade` = 淡出，`dissolve` = 交叉溶解

#### 背景

```
@bg set malias_bedroom_morning             // 默认交叉溶解（0.5s）
@bg set school_front fade                  // 黑屏过渡（1s）
@bg set school_hallway cut                 // 直切（0s）
@bg set dream_sequence slow                // 慢速淡入（2s）
```

#### CG（全屏插画）

```
@cg show window_stare fade {
  YOU: The city lights blurred through my tears.
}
```

CG 块内可嵌套对话和状态变更。块结束时自动恢复之前的背景和角色。

### 对话

对话不用 `@` 前缀，通过行首角色名（全大写）识别：

```
MAURICIO: That's not a library. That's a crime scene.
NARRATOR: Senior year. Day one.
YOU: He hasn't called me that in eight years.
```

- `CHARACTER:` — 角色对白
- `NARRATOR:` — 旁白（无角色立绘，独立样式）
- `YOU:` — MC 内心独白（斜体/特殊样式）

**语法糖**：对白 + 换表情合写：
```
MAURICIO [arms_crossed_angry]: Your call, Butterfly.
// 等价于：@mauricio expr arms_crossed_angry + MAURICIO: Your call, Butterfly.
```

### 手机/消息

```
@phone show {
  @text from EASTON: Can we talk? I miss you.
  @text to MAURICIO: How do you know where I live?
}
@phone hide
```

### 音频

```
@music play calm_morning          // 播放 BGM（循环）
@music crossfade tense_strings    // 交叉淡入新 BGM
@music fadeout                    // 淡出停止
@sfx play door_slam               // 一次性音效
```

### 游戏机制

#### 小游戏

```
@minigame qte_challenge ATK {
  @on S {
    NARRATOR: Your reflexes are razor-sharp today.
    @signal MINIGAME_PERFECT_EP01
  }
  @on A B {
    NARRATOR: Not bad. You kept up.
  }
  @on C D {
    NARRATOR: Sloppy. You're distracted.
  }
}
```

小游戏嵌入阅读流。评级结果（S/A/B/C/D）作为后续 D20 检定的修正值。`@on` 块是集内奖励叙事，不改路线。

#### 选择（D20 检定）

```
@choice {
  @option A brave "Stand your ground." {
    check {
      attr: CHA
      dc: 12
    }
    @on success {
      EASTON: Can I sit?
      @affection easton +2
      @xp +3
      @butterfly "Accepted Easton's approach"
    }
    @on fail {
      MALIA: I can't do this.
      @san -20
      @xp +1
      @butterfly "Tried to face Easton but lost courage"
    }
  }
  @option B safe "Have Mark make a scene." {
    MARK: FOOD FIGHT!
    @xp +1
    @butterfly "Had Mark create a diversion"
  }
}
```

**`@option <ID> <mode> "<text>" { }`**：
- `ID`：A/B/C/D...，`@gate` 通过此 ID 引用
- `brave`：需要 D20 检定，必须包含 `check {}` + `@on success {}` + `@on fail {}`
- `safe`：跳过检定，块内直接是叙事内容

**`check { attr: <名称>  dc: <数值> }`**：检定参数。属性名称不硬编码，脚本可使用任何名称。

D20 检定公式（引擎内置）：`D20(1-20) + 属性修正 + 小游戏修正 >= DC → 成功`

### 状态变更

```
@xp +3                                    // 经验值
@san -20                                   // 理智值
@affection easton +2                       // 好感度
@signal EP01_COMPLETE                      // 向引擎抛出事件
@butterfly "Accepted Easton's approach"    // 蝴蝶效应记录
```

`@signal` 是一个事件——引擎决定如何处理（存标记、触发成就、解锁路线）。

`@butterfly` 是叙事语义描述——引擎累积所有记录，供 `@gate type: influence` 的 LLM 判定。描述要具体，写清楚发生了什么以及它揭示了玩家的什么倾向。

### 流程控制

```
@if affection.easton >= 5 && CHA >= 14 {
  EASTON: You remembered.
} @else {
  EASTON: ...Hey.
}
```

**判定对象**：

| 对象 | 语法 |
|------|------|
| flag | `FLAG_NAME`（布尔） |
| 好感度 | `affection.<char> <op> <N>` |
| 属性 | `<ATTR_NAME> <op> <N>` |
| 经验 | `xp <op> <N>` |
| 理智 | `san <op> <N>` |

**操作符**：`>=` `<=` `>` `<` `==` `!=`
**逻辑**：`&&`（与）、`||`（或）

## Remix 兼容

Remix Executor 输出标准 `.md` 文件，格式与 Dramatizer 产出完全一致。

两种生命周期：
- **完整集替换**：生成一集或多集，放在 `remix/<session_id>/`
- **选择后片段**：用户输入替换了原 `@choice`，生成从选择点之后的全部内容

回归机制通过 `@gates` 控制：`@default main:02` 回归主线，`@default remix/abc123:02` 继续 remix 支线。

## 指令速查表

| 指令 | 说明 |
|------|------|
| `@episode <key> "<title>" { }` | 集定义 |
| `@gates { }` | 路由声明（集尾部） |
| `@gate <key> { type / trigger / condition }` | 跳转规则 |
| `@default <key>` | 兜底路线 |
| `@label <name>` / `@goto <name>` | 集内跳转（慎用） |
| `@<char> show <pose> at <pos>` | 角色入场 |
| `@<char> hide [trans]` | 角色退场 |
| `@<char> expr <pose> [trans]` | 换表情 |
| `@<char> move to <pos>` | 角色移位 |
| `@<char> bubble <type>` | 气泡动画 |
| `@bg set <name> [trans]` | 切背景 |
| `@cg show <name> [trans] { }` | CG 展示块 |
| `CHARACTER: text` | 对白 |
| `CHARACTER [pose]: text` | 对白 + 换表情 |
| `NARRATOR: text` | 旁白 |
| `YOU: text` | 内心独白 |
| `@phone show { }` / `@phone hide` | 手机界面 |
| `@text from/to <char>: content` | 短信 |
| `@music play/crossfade/fadeout` | BGM |
| `@sfx play <name>` | 音效 |
| `@minigame <id> <ATTR> { }` | 小游戏 |
| `@choice { }` | 选择块 |
| `@option <ID> <brave\|safe> "<text>" { }` | 选项 |
| `check { attr / dc }` | 检定参数 |
| `@on <cond> { }` | 条件结果块 |
| `@xp / @san / @affection` | 数值变更 |
| `@signal <event>` | 抛出事件 |
| `@butterfly "<desc>"` | 蝴蝶效应 |
| `@if <cond> { }` / `@else { }` | 条件分支 |
