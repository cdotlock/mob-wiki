---
title: Lunascripts (LS) 格式规范
tags: [ls, script-format, visual-novel, specification]
sources:
  - /Users/Clock/lunaverse/lunascripts/LS-SPEC.md
  - /Users/Clock/lunaverse/lunascripts/docs/JSON-OUTPUT.md
  - /Users/Clock/lunaverse/lunascripts/docs/ENGINE-INTEGRATION.md
created: 2026-04-15
updated: 2026-06-04
---

Lunascripts（LS）是 MobAI 互动视觉小说的脚本标记语言。一个 `.md` 文件描述一集的全部内容——场景、角色、对话、音频、D20 检定、小游戏、分支路由——由 Go 解释器编译为 JSON 供前端播放器消费。

> **2026-06-04 大幅 redesign**：删除约一半的旧指令冗余、统一 gate/ending、operand 出现在 comparison 两侧、新增 MAX/MIN 聚合、同屏一人 + 隐式 hide 规则。变更详情见 [[concepts/ls-spec-redesign-2026-06]]。本页是新规范的快照。

解释器实体见 [[entities/lunascripts]]。

## 设计原则

1. **单一格式统一叙事与游戏机制**：不分剧本文件和数据文件，一个 `.md` 搞定一切
2. **自包含**：每个文件包含一集所需的全部信息，不依赖外部清单
3. **LLM 友好**：由 Dramatizer 和 Remix Executor（LLM 管线）生成，语法对 LLM 自然
4. **素材解耦**：脚本只写语义名，解释器通过独立 `mapping.json` 翻译为 OSS URL
5. **并发分组**：`@` / `&` 前缀让编译器自动生成并发执行组，引擎无需猜测时序
6. **同屏一人**：屏幕上任何时刻只有 1 个角色立绘；位置由引擎从 `gamestate.MC` 派生（MC 左，其他右）；作者不操心 position

## 三种语法

LS 文件内交替使用三种语法：

**1. 顺序指令 `@`**：每个 `@` 开始一个新的执行步骤。
```
@bg set school_hallway fade
@mauricio neutral_smirk
```

**2. 并发指令 `&`**：加入前一个 `@` 的步骤组，同时执行。
```
@bg set school_hallway fade        // 新步骤组
&music tense_strings               // 并发
&mauricio neutral_smirk            // 并发
```

**3. 对话行**：角色名大写 + 冒号，始终独立步骤。
```
MAURICIO: Hey, Butterfly.
NARRATOR: Senior year. Day one.
YOU: He hasn't called me that in eight years.
```

语法糖：`CHARACTER [pose]: text` = 换 pose + 对话合写（desugar 为 `@<char> <pose>` + `CHARACTER: text` 两步）。

## 完整指令表

### 结构
| 指令 | 说明 |
|------|------|
| `@episode <branch_key>:<seq> "<title>" { }` | 集定义（根块） |
| `@gate { }` | **唯一**终态块（每集必须有；leaves 可混搭 @next 和 @end） |
| `@if (<cond>) { } [@else if/@else]` | 条件分支 |
| `@choice { @option ... }` | 玩家选择菜单 |
| `@option <ID> <safe\|brave> "<text>" { }` | 单个选项 |
| `@pause` | 单击等待（无参数；多击就重复指令） |

**终态规则**：每集必须以 `@gate { ... }` 收尾。Gate 内 leaves 是 `@next <branch_key>` 或 `@end <type>` 两种之一，可以在同一个 if/else 链里自由混搭。**不再有顶层 `@ending` 指令**；纯无条件 `@gate { @end TYPE }` 编译器自动 lower 为 `episode.ending` 顶级字段（Scheme B），其他形态保留 gate 结构。

### 视觉
| 指令 | 说明 |
|------|------|
| `@<char> <pose> [transition]` | 角色入场 / 换 pose（同一指令，引擎自己决定是 first show 还是 pose swap） |
| `@<char> bubble <type>` | 气泡动画（`bubble` 是保留字，pose 不能叫 bubble） |
| `@bg set <name> [transition]` | 切背景 |
| `@cg <name> "<content>"` | CG（leaf，单行；无 block，无 duration，无 transition） |

**没有指令**：`hide`、`look`、`move`、`at <pos>` 全部不存在。角色离场是隐式的——下一个 `@<char> <pose>`、`NARRATOR:`、`YOU:` 都会清掉当前角色。位置由引擎从 `gamestate.MC` 派生（MC 左，其他右），脚本里无 position 字段。

**Transition**：`fade` `cut` `slow` `dissolve`（不写 = 默认）。

**Bubble types**（9 种）：`anger` `sweat` `heart` `question` `exclaim` `idea` `music` `doom` `ellipsis`。

**CG**：现在是纯 leaf。`content` 是英文连续叙述（镜头怎么走、情节强调什么），下游 agent-forge 用这段 prose 渲染短视频。**CG 期间不能叠对白**——对白要移到 `@cg` 行之前或之后。

### 对话
| 语法 | 说明 |
|------|------|
| `CHARACTER: text` | 角色对白 |
| `CHARACTER [pose]: text` | 对白 + 换 pose（语法糖）|
| `NARRATOR: text` | 旁白 |
| `YOU: text` | 内心独白 |

### 角色键一致性（speaker ↔ asset key 1:1）

**核心原则**：`<NAME>:` 说话人标签必须等于 `uppercase(asset_key)`，asset_key 来自 `mapping.json` `assets.characters`。LS 解释器靠**大小写不敏感的单 token 相等**把 `MAURICIO:` 匹配到 `@mauricio`，所以标签必须是单一 `[A-Z_]+` token——**不能有点、空格、敬称**。

| 错误 | 正确 | 原因 |
|------|------|------|
| `MRS. KING:` | `MRS_KING:` | `.` 和空格让 parser 把 `MRS.` 当成第一个 token。asset_key 是 `mrs_king`。 |
| `MR. THOMAS:` | `MR_THOMAS:` | 同上 |
| `DR JONES:` | `DR_JONES:` | 内部空格违反 `[A-Z_]+`。asset_key 是 `dr_jones`。 |

**前端显示名 ≠ 标签**：屏幕上看到的 "Mrs. King" 由引擎从角色 profile 读取（character.display_name 或 i18n 表），与脚本里的 `MRS_KING:` 标签是两回事。脚本只关心键，不关心呈现。

**`@<char>` 同样规则**：`@<char> <pose>` 或 `@<char> bubble <type>` 里的 char 必须存在于 `mapping.json` `assets.characters`。如果某个剧情节拍需要无立绘的角色（楼下喊人的妈、路过的群演、电话那头的声音），**不要发明 `@mama_reyes`**。三选一：

1. `@sfx <name>` — 如果有匹配音效（如 `mama_calls_dinner`）
2. 纯 `NARRATOR:` 一行旁白（"楼下妈妈喊吃饭"）
3. `@<onscreen_char> bubble exclaim` — 反应方的气泡，不是说话方的缺位立绘

**审计 recipe**（写完一集跑这个，确保零 orphan）：

```bash
# 1. 列所有说话人标签
awk '/^[[:space:]]*[A-Z][A-Z_. ]*:[[:space:]]/ {match($0,/^[[:space:]]*[A-Z][A-Z_. ]*:/); print substr($0,RSTART,RLENGTH)}' ep_NN.md | sort -u

# 2. 列所有 @<char> 引用（pose 形式或 bubble 形式）
grep -oE '@[a-z_]+ ([a-z_]+|bubble [a-z_]+)' ep_NN.md | awk '{print $1}' | sort -u

# 3. 取 mapping.json 的合法字符键
jq -r '.assets.characters | keys[]' ls-build/mapping.json | sort

# 三个集合相交：所有说话人标签的小写形式必须 ⊆ 字符键集合（除 NARRATOR/YOU），所有 @<char> 必须 ⊆ 字符键集合。
```

**真实 bug 史**（沉淀于 2026-04-27 no-rules VN-cut trial）：

- `MRS. KING:` 在 EP3 出现 8 次 → LS parser 错误 → JSON 输出里 0 条 mrs_king dialogue → 前端跳过整段戏。修复：sed 替换为 `MRS_KING:`，重新编译，8 条 dialogue 节点全部 emit。
- `@mama_reyes` 在 EP1 结尾出现 → mapping.json 里没有 mama_reyes 字符键 → 编译时静默忽略（或渲染时抓不到 PNG 报 404）。修复：替换为 `@sfx mama_calls_dinner`。

### 同屏一人 + 说话即显形（与旧规则的核心差异）

**新规则**：屏幕上同一时刻只有 1 个角色立绘。任何引发"换人"的事件都会清屏后再 show 新角色：

- 新的 `@<char> <pose>` 触发：清旧 → show 新
- `NARRATOR:` 或 `YOU:` 触发：清屏（旁白/独白时画面无角色）
- 不同角色的 `<CHAR>:` 对白触发：清屏 → show 说话角色
- `@phone { ... }` 期间：保持当前角色，phone overlay 之上叠加

**意味着什么**（与旧 spec 的关键差异）：

旧 spec 里作者需要在每个 `@bg set` 之后**显式** `@<char> show ... at <pos>`，否则 `@<char> look` 是 no-op。新 spec 里这条规则**更强、但更自动**：

- 作者**不需要**写 `@<char> show` —— 任何 `@<char> <pose>` 都会自动让该角色入场
- 作者**不需要**写 `@<char> hide` —— 切场景 / 旁白 / 换人时引擎自己清
- 作者也**不能**让两个角色同屏。如果一段戏想表达"两人对峙"，就让对白快速来回切换角色，每条 dialogue 触发对应立绘 swap

**潜在意图坑**：希望角色看到对方的反应。例如：

```ls
@josie half_smile_smug
JOSIE: 九月份穿高领。
@malia red_lipstick_armored_senior     // ✓ 切到 malia
MALIA: 暴露狂一个。
                                       // 此时 josie 立绘已经被清
// 如果想表达"josie 听完皱眉"，必须 @josie 再回来一次
@josie eyebrow_raise_skeptical
JOSIE: ...
```

CG 是叠加在场景之上的视频段，不打断 char_show 状态。`@phone { ... }` overlay 也不打断。

**审计 recipe**（更新版）：

```bash
# 列出所有 @<char> pose 切换
grep -oE '@[a-z_]+ [a-z_]+' ep_NN.md | sort | uniq -c | sort -rn

# 找潜在意图问题：同一行 dialogue 后既没切换 pose 也没切人，但下条 dialogue 是另一角色
# (人工 review；现在没有 fixer 工具，因为新规则下场景非常简单)
```

### 音频
| 指令 | 说明 |
|------|------|
| `@music <name>` | 设置 BGM（引擎自动决定 from-silence 还是 crossfade） |
| `@music stop` | 停止 BGM（隐式 fadeout） |
| `@sfx <name>` | 音效（one-shot） |

**没有指令**：`@music play / crossfade / fadeout`、`@sfx play` 全部不存在——简化为单一 set/stop 模型。

### 手机 / 短信
| 指令 | 说明 |
|------|------|
| `@phone { @text ... }` | 手机 overlay 块（无 show/hide；块结束 = overlay 收起）|
| `@text from <char>: <content>` | 入站短信（左气泡） |
| `@text to <char>: <content>` | 出站短信（右气泡） |

**块内白名单**：`@phone { ... }` 内**只允许 `@text from/to`**。任何其他指令（narrator、char、music、signal、if 等）都会触发 validator 错误。要做旁白叠加，把它放在 `@phone` 块之外。

### 游戏机制
| 指令 | 说明 |
|------|------|
| `@trick <type> "<prompt>"` | 强制 body interaction（6 种 type 锁定：tap/hold/swipe/shake/swing/tilt） |
| `@minigame <name> "<description>"` | 可选嵌入 H5（leaf，无 body；description 是 prose） |
| `@choice { @option ... }` | 玩家选择块 |
| `@option <ID> safe "<text>" { }` | 安全选项 |
| `@option <ID> brave "<text>" { check { attr: X dc: N } @if (check.success) { } [@else { }] }` | 勇敢选项（D20 检定） |

- brave option 的 success/fail 分支用 `@if (check.success) { } @else { }`
- `check.success` / `check.fail` 是 brave option 体内合法的 context-local 条件
- `@minigame` 第二位参数是英文 prose 描述（必填），下游 vibe-coding agent 用来生成 H5

### 状态变更
| 指令 | 说明 |
|------|------|
| `@affection <char> +/-N` | 好感度 delta |
| `@signal mark <NAME>` | 持久布尔标记（可被 `@if (NAME)` 查询） |
| `@signal int <name> <=\|+\|-> <N>` | 持久整数变量 mutate |
| `@butterfly "<desc>"` | 蝴蝶效应记录（喂 Remix/Dream，**不参与 gate routing**） |
| `@achievement <id> { name / rarity / description }` | 成就解锁（块内含完整 metadata） |

**Signal**：mark 用于"重要剧情点的可查询布尔"；int 用于"counter / threshold 的整数变量"。**不要把 mark 当 counter 用**（语义不同：mark 是 set-once-true，int 是可加可减）。

**Butterfly 角色重构**：旧 spec 里 butterfly 喂 `@if (influence "...")` 做 gate routing，新 spec **删除了 influence condition**——butterfly 现在仅作为内容生成器（Remix Executor + Dream）的输入。Routing 只读 signal / affection / choice 状态。

**Achievement**：单一形态——`@achievement <id> { ... }` 块既是元数据也是触发点。条件触发用外层 `@if` 包：

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
- 三字段 `name` / `rarity` / `description` 都必填；裸 `@achievement <id>` 无块是 parse error
- 同一 id 多个剧情点触发合法——引擎按 id 在 unlock 时去重

### 流程控制（Conditions + Operands）

```
@if (MAX(affection.easton, affection.diego, affection.mauricio) >= 8) {
  // 任一 LI 好感 >= 8
} @else @if (san <= 20) {
  // 主角理智低
} @else {
  // ...
}
```

**5 种 condition kind**（删除了旧 spec 的 influence；rating 由 trick/minigame 重构去除）：

| Kind | 语法 | AST 输出 | 作用域 |
|------|------|--------|-------|
| `choice` | `<ID>.<success\|fail\|any>` | `{type:"choice", option, result}` | 任意（回顾性） |
| `flag` | bare `<MARK_NAME>` | `{type:"flag", name}` | 任意 |
| `comparison` | `<operand> <op> <operand>` | `{type:"comparison", left, op, right}` | 任意 |
| `compound` | `<cond> && <cond>` / `<cond> \|\| <cond>` | `{type:"compound", op, left, right}` | 任意 |
| `check` | `check.success` / `check.fail` | `{type:"check", result}` | **仅 brave option 体内** |

**comparison 的 left 和 right 都是 operand**（不再像旧 spec 那样 right 必须是 int）。

**5 种 operand kind**：

| Kind | 语法 | AST 输出 |
|------|------|--------|
| `literal` | `5` / `-3` | `{kind:"literal", value:N}` |
| `affection` | `affection.<char>` | `{kind:"affection", char}` |
| `value` | bare `<name>`（signal int 或引擎数值如 san/CHA） | `{kind:"value", name}` |
| `max` | `MAX(<op>, <op>, ...)` | `{kind:"max", args:[op,op,...]}` |
| `min` | `MIN(<op>, <op>, ...)` | `{kind:"min", args:[op,op,...]}` |

**MAX / MIN 是大写保留字**：args 数量 >= 2，无上限，可递归嵌套。小写 `max` / `min` 仍是合法的 value name。

变量对变量比较合法：`@if (affection.easton > affection.diego)`、`@if (5 < affection.x)`（字面在左）、`@if (MAX(affection.easton, affection.diego) > affection.mauricio)`。

## Gate 路由（统一终态）

```
@gate {
  @if (san <= 0): @end bad_ending
  @else @if (A.fail): @next main/bad/001:01
  @else @if (MAX(affection.easton, affection.diego) >= 8): @end complete
  @else: @next main:02
}
```

**Leaves 可自由混搭**：`@next <branch_key>` 和 `@end <type>` 出现在同一 if/else 链里没限制。3 种 ending type：`complete` / `to_be_continued` / `bad_ending`。

**最小形态**：
```
@gate { @next main:02 }                    // 纯路由
@gate { @end bad_ending }                  // 纯终态（编译器 lower 为 episode.ending）
@gate { @if (cond): @end X / @else: @next Y }  // 混合
```

**Coverage 规则**：gate 必须有完整覆盖——要么单个无条件 leaf，要么完整 if/else 链（最后一个 route 必须是无条件 `@else`）。否则 validator 报 `INCOMPLETE_GATE`。

**JSON shape**：见 [[concepts/ls-spec-redesign-2026-06]] "JSON 输出 Breaking Changes / Gate 形态" 一节。

## 命名与寻址

文件路径即 episode_id：`novel_<id>/main/01.md` → `main:01`，`novel_<id>/main/bad/001/01.md` → `main/bad/001:01`。

`@episode <branch_key>:<seq> "<title>"` 头里的 `branch_key:seq` 必须与文件路径派生的值一致（validator 校验）。

详见 [[concepts/stable-step-id]]。

## Remix 兼容

Remix 脚本格式完全一致，branch_key 使用 `remix/<session_id>:01`。通过 gate `@else: @next main:02` 回归主线。

## 引擎不可修改的值

XP、SAN/HP 等数值由游戏引擎内部管理，脚本不能 mutate，只能在 `@if` 条件中读取（如 `@if (san <= 20)`）。

## 历史变更

- **2026-06-04** 大幅 redesign：详见 [[concepts/ls-spec-redesign-2026-06]]
- **2026-05-19** trick/minigame redesign：trick 锁 6 种、minigame 改 leaf prose-driven、删 rating condition
- **2026-04-27** stable step-id：内容寻址 cursor，AchievementStep id 改名
- **2026-04-23** signal int 后台支持
