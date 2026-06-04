---
title: MSS Spec Redesign (2026-06-04)
tags: [mss, redesign, spec-change, decision-record, breaking-change]
sources:
  - /Users/Clock/moonshort/moonshort-script/MSS-SPEC.md
  - /Users/Clock/moonshort/moonshort-script/docs/JSON-OUTPUT.md
  - /Users/Clock/moonshort/moonshort-script/docs/ENGINE-INTEGRATION.md
created: 2026-06-04
---

# MSS Spec Redesign (2026-06-04)

一次性大幅简化 MSS 源语言 + JSON 输出形态。Go 编译器、所有测试、testdata、skills 已全量对齐。落地 commit 5 个，pushed to `cdotlock/moonshort-script@main`：

```
35a6721 Sync skills + reference docs with new MSS spec
155dff8 Regenerate testdata for new MSS spec
321cb9e Refactor Go compiler for new MSS spec
95b7ff3 Fix 'assests' typo in mss decompile output filename
aeaacb1 Rewrite MSS spec: unify gate/ending, operand AST, MAX/MIN aggregate
```

## 为什么 redesign

旧 spec 累积了若干让作者和引擎都重复操心的设计：

- `@<char> show / hide / look / move + at <pos>` 4 个动词 + position 三档让作者每次都决定"谁在哪里" —— 但实际上只有「MC 在左」「其他在右」「一次一个」三条规则被遵守
- `@gate` 与 `@ending` 二选一让 mixed routing（多数 next + 少数 end）无法直接表达
- `@if` comparison 的右侧硬编码为 int 字面，无法做变量对变量比较（如 LI 之间好感度对比）
- `@music play / crossfade / fadeout` 三种 + `@sfx play` 让作者操心音频状态机
- `@phone show {} @phone hide` 多此一举（block 本身就是 lifecycle）
- `@pause for N` 给作者一个"N 是几"的微决策
- `@cg show <name> [transition] { duration: …, content: "…", body 节点 }` 把作者负担拉到极致
- `@label` / `@goto` 在已有 `@if/@else` 的语言里属于功能重复
- `@if (influence "...")` 把 routing 决策权交给 LLM——但 butterfly 的真正用途是喂 Remix Executor / Dream，不是路由

每条都不大，但叠起来就让 Dramatizer 提示词膨胀、引擎实现复杂、testdata 难维护。

## 决策摘要

| 旧 | 新 |
|---|---|
| `@<char> show <pose> at <pos> [transition]` | `@<char> <pose> [transition]` |
| `@<char> hide` | 删除（同屏一人隐式接管） |
| `@<char> look <pose>` | `@<char> <pose>`（合并） |
| `@<char> move to <pos>` | 删除 |
| `@<char> bubble <type>` | 保留；`bubble` 升保留字 |
| `@phone show { ... } @phone hide` | `@phone { @text from/to ... }`（块内白名单：只允许 @text） |
| `@music play X` / `crossfade X` | `@music X`（引擎自动 from-silence vs crossfade） |
| `@music fadeout` | `@music stop` |
| `@sfx play X` | `@sfx X` |
| `@pause for N` | `@pause`（多击就重复指令） |
| `@cg show X [trans] { duration: …, content: "…", body … }` | `@cg X "<content>"`（leaf；对白移到 @cg 之前/之后） |
| `@label X` / `@goto X` | 删除（用 @if/@else 替代） |
| 顶层 `@ending X` | `@gate { @end X }`（gate 内 leaf） |
| `@if (influence "...")` | 删除（butterfly 不再参与路由） |
| `@if ("...")` 裸字符串 | 删除 |
| comparison right 必须 int | left/right 都是 operand（5 kinds） |
| —— | **新增**：`MAX(op, op, …)` / `MIN(op, op, …)`（args >= 2，可嵌套） |
| —— | **新增**：变量对变量比较 `affection.x > affection.y` |
| left/center/right 三档位置 | 删除（MC 左，其他右，引擎从 gamestate.MC 派生） |

`MAX` / `MIN` 是**大写**保留字；小写 `max` / `min` 仍可作为 value name（引擎数值 or signal int）。

## JSON 输出 Breaking Changes

**最关键 —— 影响 engine + overlay 系统。**

### 删除的 step type
```
char_hide  char_look  char_move
phone_hide
music_play  music_crossfade  music_fadeout
sfx_play
label  goto
```

### 改名的 step type
| 旧 | 新 |
|---|---|
| `char_bubble` | `bubble` |
| `music_play` | `music` |
| `sfx_play` | `sfx` |
| —— | `music_stop`（新增） |

### 字段变化
- `char_show`：删除 `position` 字段，引擎从 `gamestate.MC` 派生（MC 左，其他右）
- `cg_show`：**leaf**——没有 `steps` 数组、没有 `duration`、没有 `transition`。只有 `name` + `content`（+ `url`）
- `pause`：没有 `clicks` 字段
- `music`：fields 是 `{name, url}`，无 play/crossfade 之分
- `music_stop`：空 step（无字段）

### Gate 形态
```jsonc
// 单条无条件 leaf — 两种
{ "next": "main:02" }
{ "end": "bad_ending" }

// if/else 链 — leaves 可自由混搭 next 和 end
{
  "if": { ... },
  "next": "main:01",
  "else": {
    "if": { ... },
    "end": "bad_ending",
    "else": { "next": "main:99" }
  }
}
```

`resolveGate()` 需要：
1. 检查节点含 `next` 字段还是 `end` 字段
2. `end` 时结束 episode 而不是路由
3. `end` 的 type ∈ `complete | to_be_continued | bad_ending`

### `Episode.ending` 字段（保留但语义变了）
仍然存在，**但只作为 emitter 的 Scheme-B lowering 产物**：当 source 是 `@gate { @end TYPE }`（单条无条件 end）时，编译器把 `gate` 设为 `null`、`ending = {type: TYPE}`。其他形态都保留为 gate 结构。引擎兼容代码可以保留。

### Comparison condition.right 变了
旧：`"right": 5`（int）
新：`"right": {kind: "literal", value: 5}`（operand 对象）

### Operand 5 种 kind（任意位置可出现）
```jsonc
{ "kind": "literal",   "value": 5 }
{ "kind": "affection", "char": "easton" }
{ "kind": "value",     "name": "san" }        // 引擎数值 OR signal int
{ "kind": "max",       "args": [op, op, ...] }
{ "kind": "min",       "args": [op, op, ...] }
```

- `max` / `min` 的 args 数组**长度 >= 2，无上限**，可以**递归嵌套**
- 引擎需要一个递归 `evaluateOperand` 函数（参考 `docs/ENGINE-INTEGRATION.md`）

### 删除的 condition kind
`influence` 不复存在。引擎里如果有 `case "influence":` 分支可以删了。剩 5 种：`choice / flag / comparison / compound / check`。

## 引擎行为变化（同屏一人 + 隐式 hide）

`char_show` 再也不显式 hide。引擎必须自己维护：

- 同一时刻屏幕上**只能有 1 个角色** sprite
- 新的 `char_show` 触发：如果当前已有角色，先清屏再 show 新角色
- `narrator` / `you` step 触发：清屏（旁白/内心独白时不显示任何角色）
- `dialogue`（带 `character` 字段）触发：如果说话角色不是当前显示的，清屏再 show 说话角色
- `phone_show` 期间：保持当前角色，phone overlay 之上叠加
- 位置：引擎从 `gamestate.MC` 派生（MC=left，others=right），脚本里没有 position 字段

伪代码见 `docs/ENGINE-INTEGRATION.md` 里 "character visibility management" 一节。

## Butterfly 角色重构

`@butterfly "<desc>"` 指令保留，**但用途变了**：

- **旧**：喂 gate routing（`@if (influence "...")` 读取）
- **新**：仅作为内容生成器的输入：
  - **Remix Executor**：根据 butterfly 历史合成 remix 剧本
  - **Dream**：根据 butterfly 历史合成 dream 段落

Gate routing 现在只读 signal mark / signal int / affection / choice 状态。

## MAX/MIN 聚合的设计点

- 大写保留字 `MAX` / `MIN`，args 数量任意（下限 2，**无上限**）
- args 可以是任意 operand kind（literal / affection / value / 嵌套 MAX/MIN）
- 典型用法：「任一 LI 好感度 >= 8 触发结局」`@if (MAX(affection.easton, affection.diego, affection.mauricio, affection.elias) >= 8): @end complete`
- 比较「主角偏好谁」`@if (affection.easton > MAX(affection.diego, affection.mauricio, affection.elias)): @next main/route/easton:01`
- 小写 `max` / `min` 仍可作为 value name（引擎数值 或 signal int 名）

## 下游代码影响清单

| 仓库 / 文件 | 改动方向 |
|---|---|
| `moonshort-backend/engine/StepPlayer.ts` | 删除旧 step type case；新增 bubble/music/music_stop/sfx case；char_show 实现隐式 hide；从 gamestate.MC 派生位置；cg_show 视为 leaf；pause 不读 clicks；comparison.right 用 operand evaluator；删 influence |
| `moonshort-backend/app/core/episode-overlay/apply-overlays.ts`（~1000 行，30+ gate 引用）| `GateRoute.Target` 字段没了，改为 `Leaf` interface（next 或 end）；遍历每条 route 时检查 leaf kind |
| `moonshort-backend/app/services/save-action-service.ts` | `resolveGate` 内部要处理 end leaf 终结 episode 的逻辑 |
| Dramatizer / Remix Executor / Dream 提示词 | 改成新语法；butterfly 角色重述；引用 root `MSS-SPEC.md` |
| `api_server.py` | 二进制接口未变；若有引用 `assests_mapping.json` 旧名要改为 `assets_mapping.json`（CLI 输出文件名已修） |
| agent-forge（CG 渲染管线）| CG 现在只有 `content` 字段，没有 duration/body；camera/timing 全由 content 文本驱动 |
| 任何依赖 `Episode.ending` 字段的代码 | 仍然存在，但只在 Scheme-B 单 leaf 形态下被填，其他形态需要遍历 gate |

## 迁移注意（DB 里已有老 JSON 剧本）

旧 episode JSON 含有 `char_hide` / `music_play` / 等已删 step type、`position` 字段、`right` 为 int 等。如果引擎需要兼容旧数据：

- 推荐写一次性 migration：旧 step type → 删除/改名；comparison.right int → `{kind: "literal", value: N}`；gate route `target` string → `{next: target}`
- 或保留 dual-mode 解析（旧 + 新），引擎里加 fallback case；**但新生成的 JSON 不会再有旧 type**

新 binary 跑新 source 输出的 JSON 已经验证 round-trip byte-identical（feature_parade 的 ep01 / ep02 / stress 三个剧本）。

## 验证脚本

```bash
cd ~/moonshort/moonshort-script
go build -o bin/mss ./cmd/mss
go test ./... -count=1          # 全过（7 个 package）

# round-trip 检验
./bin/mss compile testdata/feature_parade/stress.md \
  --assets testdata/feature_parade/mapping.json \
  -o /tmp/a.json
./bin/mss decompile /tmp/a.json -o /tmp/decomp/
./bin/mss compile /tmp/decomp/mss.md \
  --assets /tmp/decomp/assets_mapping.json \
  -o /tmp/b.json
diff /tmp/a.json /tmp/b.json     # identical
```

## 权威文档

- `MSS-SPEC.md` — 源语言完整规范
- `docs/JSON-OUTPUT.md` — JSON 结构 + step 类型表
- `docs/ENGINE-INTEGRATION.md` — 引擎集成伪代码
- `skills/mss-scriptwriting/SKILL.md` — 写作 skill（喂 Dramatizer / Remix）
- `testdata/feature_parade/README.md` — 测试矩阵 [T##]

`skills/mss-scriptwriting/references/MSS-SPEC.md` 现在是 root MSS-SPEC.md 的 verbatim mirror —— 改 root 即可，mirror 同步。

## 相关页面

- [[concepts/mss-format]] — 当前规范（本次 redesign 后已重写）
- [[entities/moonshort-script]] — Go 解释器实体
- [[concepts/stable-step-id]] — step ID 寻址（未变）
- [[concepts/cg-pipeline]] — CG 三层管线（CG 已改 leaf；需要确认 cg_collector 是否解析新形态）
- [[concepts/signal-int-backend]] — signal int 后端（未变）
- [[concepts/dream-bonus-only-op]] — dream 系统（butterfly 是它的输入之一）
