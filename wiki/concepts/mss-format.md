---
title: MoonShort Script (MSS) 格式规范
tags: [mss, script-format, visual-novel, specification]
sources: []
created: 2026-04-15
updated: 2026-04-27
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

### 角色键一致性（speaker ↔ asset key 1:1）

**核心原则**：`<NAME>:` 说话人标签必须等于 `uppercase(asset_key)`，asset_key 来自 `mapping.json` `assets.characters`。MSS 解释器靠**大小写不敏感的单 token 相等**把 `MAURICIO:` 匹配到 `@mauricio`，所以标签必须是单一 `[A-Z_]+` token——**不能有点、空格、敬称**。

| 错误 | 正确 | 原因 |
|------|------|------|
| `MRS. KING:` | `MRS_KING:` | `.` 和空格让 parser 把 `MRS.` 当成第一个 token，触发 `INVALID_TRANSITION`。asset_key 是 `mrs_king`。 |
| `MR. THOMAS:` | `MR_THOMAS:` | 同上 |
| `DR JONES:` | `DR_JONES:` | 内部空格违反 `[A-Z_]+`。asset_key 是 `dr_jones`。 |

**前端显示名 ≠ 标签**：屏幕上看到的 "Mrs. King" 由引擎从角色 profile 读取（character.display_name 或 i18n 表），与脚本里的 `MRS_KING:` 标签是两回事。脚本只关心键，不关心呈现。

**`@<char>` 同样规则**：`@<char> show|look|hide|bubble` 里的 char 必须存在于 `mapping.json` `assets.characters`。如果某个剧情节拍需要无立绘的角色（楼下喊人的妈、路过的群演、电话那头的声音），**不要发明 `@mama_reyes`**。三选一：

1. `@sfx play <name>` — 如果有匹配音效（如 `mama_calls_dinner`）
2. 纯 `NARRATOR:` 一行旁白（"楼下妈妈喊吃饭"）
3. `@<onscreen_char> bubble exclaim` — 反应方的气泡，不是说话方的缺位立绘

**审计 recipe**（写完一集跑这个，确保零 orphan）：

```bash
# 1. 列所有说话人标签
awk '/^[[:space:]]*[A-Z][A-Z_. ]*:[[:space:]]/ {match($0,/^[[:space:]]*[A-Z][A-Z_. ]*:/); print substr($0,RSTART,RLENGTH)}' ep_NN.md | sort -u

# 2. 列所有 @<char> 引用
grep -oE '@[a-z_]+ (show|look|hide|bubble)' ep_NN.md | awk '{print $1}' | sort -u

# 3. 取 mapping.json 的合法字符键
jq -r '.assets.characters | keys[]' mss-build/mapping.json | sort

# 三个集合相交：所有说话人标签的小写形式必须 ⊆ 字符键集合（除 NARRATOR/YOU），所有 @<char> 必须 ⊆ 字符键集合。
```

**真实 bug 史**（沉淀于 2026-04-27 no-rules VN-cut trial）：

- `MRS. KING:` 在 EP3 出现 8 次 → MSS parser INVALID_TRANSITION → JSON 输出里 0 条 mrs_king dialogue → 前端跳过整段华夫饼厨房戏。修复：sed 替换为 `MRS_KING:`，重新编译，8 条 dialogue 节点全部 emit。
- `@mama_reyes bubble exclaim / @mama_reyes hide` 在 EP1 结尾出现 → mapping.json 里没有 mama_reyes 字符键 → 编译时静默忽略（或渲染时抓不到 PNG 报 404）。修复：替换为 `@sfx play mama_calls_dinner`（mapping.json 里已有的 sfx）。

### 角色入场必须显式（`@bg set` 清空 → 必须 `@<char> show`）

**核心原则**：MSS 玩家引擎在每次 `bg` step 都做硬清舞台 — 三个角色槽 `charLeft / charCenter / charRight` 一并归零。`@<char> look <pose>` 在角色不在台上时是 **no-op**（不会自动 show）。「单可见槽」渲染规则又让 active speaker 的槽优先显示，找不到 speaker 才退化到「最近 epoch」槽。三条规则叠起来，得到一条强约束：

> **每个 scene 里凡是要说话的角色，都必须在该 scene 里被 `@<char> show <look> at <pos>` 过一次，然后才能讲第一句台词。**

不遵守这条规则的可见症状：bubble 标签写着说话人 A，画面上的立绘却是 B（A 从未在本场景被 `show`，引擎退化到 B 这个最近被 `show` 的槽）。

**正确写法**：

```mss
@bg set school_parking_lot dissolve   # 清空所有 3 个槽
@malia show red_lipstick_armored_senior at center   # ✓ 协议人入场
@josie show half_smile_smug at left                 # ✓ 对手入场
NARRATOR: Josie 靠在铁丝网边等着。
JOSIE: 九月份穿高领。我最好的朋友,懦夫一个。
MALIA: 我最好的朋友,暴露狂一个。   # ✓ 已经在台上,bubble + sprite 同步
```

**错误写法**：

```mss
@bg set school_parking_lot dissolve   # 清空
@josie show half_smile_smug at left   # Josie 入场
@malia look red_lipstick_armored_senior   # ✗ malia 不在台上,no-op
JOSIE: ...
MALIA: 我最好的朋友,暴露狂一个。   # ✗ bubble 说 malia,画面上只有 josie
```

**`@<char> look` 的真正用途**：在已经 `show` 过的角色身上**改表情**。比如 `MALIA` 已经在台上的 `red_lipstick_armored_senior` 立绘，剧情中她皱了一下眉，可以 `@malia look red_lipstick_half_cracked_after_school` 切到另一张同角色立绘。它不能代替 `@<char> show`。

**协议人不豁免**：哪怕脚本里 MC 是 protagonist（no-rules 里是 `@malia`），写作直觉上"她当然在场"，引擎也照样需要每个 scene 都 `@malia show ... at <pos>`。

**审计 recipe**：

```bash
# 跑自动 fixer 的 dry-run,列出所有 offstage speaker + orphan look
python3 tools/fix_offstage_speakers.py            # 只打印计划
python3 tools/fix_offstage_speakers.py --apply    # 自动在每个 @bg set 之后插入缺失的 @<char> show
```

fixer 算法：每个 scene（`@bg set` 分隔），收集 (a) 所有有 `<CHAR>: ...` dialogue 的角色，(b) 所有有 `@<char> look` 但前面没 `@<char> show` 的角色。两类都要补一行 `@<char> show <last_known_look> at <pos>`，位置启发：每个角色有偏好槽（malia=center / easton=left / mauricio=left / josie=left / mark=left / ...），冲突时退到空槽。

**真实 bug 史**：

- 2026-04-27：no-rules-vn-zh EP1 s04 parking lot 看到「bubble: malia / sprite: josie」错配。挖到根因：脚本只 `@josie show ... at left` 然后 `@malia look ...`（orphan）。引擎把 josie 当成 fallback。修复：在 `@bg set` 后立刻补 `@malia show red_lipstick_armored_senior at center`，josie 仍在 left。zh EP1-3 共 30 个 orphan look + 186 个 offstage dialogue 一次性扫清。
- 同 bug 同时存在于 en EP1-3（结构相同的脚本）。后续按 user 指示决定是否修。

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
