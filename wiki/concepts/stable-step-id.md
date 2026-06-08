---
title: Stable Step ID & Content-Addressed Cursor
tags: [lunaverse, backend, ls, cursor, remix, addressing]
sources: [docs/superpowers/specs/2026-04-26-stable-step-id-design.md]
created: 2026-04-27
updated: 2026-04-27
---

# Stable Step ID & Content-Addressed Cursor

2026-04-27 上线。把 `Session.cursor` 从「位置寻址」改为「内容寻址」——每个 LS step 在编译期带上稳定字符串 ID（如 `0021_dlg`、`0021p0001p0001_char`），cursor segment 用 ID 而非数组下标。Splice / replace 类结构变更对 cursor 透明：cursor 唯一会失败的方式是指向被删除的 step，且失败 fail-fast（lookup miss → undefined），不再静默错位。

## 为什么需要

Cursor drift 是这个 codebase 反复出现的 bug 类。2026-04 月就被同一根因咬到 5 次：

| 日期 | 症状 |
|---|---|
| 04-17 | concurrent group 嵌入 decision step 走错 |
| 04-18 | 新 session 跳过开场对白 |
| 04-23 | `validateForwardCursor` 拒绝合法嵌套 cursor |
| 04-24 | `apply-patches` 输出全 orphan（找不存在的 `step.id`） |
| 04-26 | Remix 后客户端读未打 patch 的 episode → walker 在 4 行循环 |

根因都一样：**cursor 用数组下标定位 step**。任何 splice/replace 都让下标错位，cursor 自己看不出来。

修复思路：cursor 是结构性正确性，不是维护纪律。给每个 step 编译期注入稳定 ID，cursor 改用 ID 寻址 → splice/replace 完全透明。

## ID 格式

```
<seq>_<type>
```

### type tag（2-4 字母）

固定映射，由 [[entities/lunascripts]] 编译器从 LS step type 派生：

| LS type | tag | LS type | tag |
|---|---|---|---|
| `dialogue` | `dlg` | `bg` | `bg` |
| `narrator` | `nar` | `char_show` / `char_hide` / `char_look` / `char_move` / `bubble` | `char` |
| `you` | `you` | `music_play` / `music_crossfade` / `music_fadeout` | `mus` |
| `pause` | `pau` | `sfx_play` | `sfx` |
| `choice` | `ch` | `phone_show` / `phone_hide` / `text_message` | `phn` |
| `minigame` | `mg` | `signal` | `sig` |
| `cg_show` | `cg` | `affection` | `aff` |
| | | `achievement` | `ach` |
| | | `butterfly` | `btf` |
| | | `if` / `goto` / `label` | `ctrl` |

Tag 只是给人和 LLM 读的注释；runtime cursor 逻辑完全不读 tag。

### seq —— 原始 step

4 位零填充计数器，**容器作用域**（每个容器从 `0001` 重启）。容器是：top-level steps、每个 `choice.options[i].steps`、`minigame.steps`、`cg_show.steps`、`if.then`、`if.else`（数组形式）、`phone_show.messages`。

**并发组不是容器**——`[stepA, stepB]` 在父容器中消耗连续两个 seq，不嵌套重启。容器作用域 + cursor 路径中的容器 escape segment 共同保证 ID 全局唯一。

```
top-level: 0001_dlg, 0002_nar, [0003_char, 0004_mus], 0005_ch, 0006_dlg
choice.options[0].steps: 0001_dlg, 0002_nar, 0003_dlg
choice.options[1].steps: 0001_dlg, 0002_dlg, 0003_nar
```

### seq —— patch 注入的 step

Backend 在 `apply-patches.ts` 注入（不是 LLM 生成）：

```
<anchorSeq>p<patchSeq>p<stepIdx>
```

- `anchorSeq` = anchor step 的 seq 部分（去掉 `_<tag>`）
- `patchSeq` = 该 anchor 上第几个 patch（按 createdAt ASC，1-based 4 位填充）
- `stepIdx` = 该 patch 步数组中第几步（1-based 4 位填充）

**关键：**`p` (ASCII 112) > `_` (ASCII 95)，所以 patch step ID 在字典序排序中**总是排在 anchor 之后**。`字典序排序 = 执行顺序`成为这个格式的核心不变量。

### 嵌套 patch（patch-on-patch）

如果 anchor 本身是 patch step，seq 会链式叠加：

```
0021_dlg                           原始第 21 步，对白
0021p0001p0001_char                第一个 patch 的第 1 步
0021p0001p0001p0003p0002_dlg       patch on (0021p0001p0001), patch 3, 步 2
```

每个 `p<patchSeq>p<stepIdx>` 描述一层嵌套。实际深度极少超过 1-2 层。

## Cursor 格式

旧 `(string|number)[]` 改为统一的 `string[]`：

```
今天: [12, "options", 2, "steps", 3]
明天: ["0012_ch", "options", "opt_marry", "steps", "0003_dlg"]
```

容器 escape segment（`"options"` / `"steps"` / `"then"` / `"else"` / `"messages"`）不变——它们本来就是字符串、本来就稳定。option 索引 `2` 改用 option 自身的 semantic id（如 `"opt_marry"`），这个 id 早就存在于 LS（之前只用作 `Session.choiceHistory` 的 key），现在提升到 cursor 系统。

## AchievementStep.id 改名

新的统一 `id` 字段和 `AchievementStep` 已有的语义 `id`（如 `"RARE_COURAGE"`）冲突。Code review 在 Task 1 抓到这个 bug——会让所有 achievement 在同一容器位置坍缩到 `0001_ach`。

解决：`AchievementStep.id` → `AchievementStep.achievement_id`，对齐 `MinigameStep.game_id` 命名习惯。LS 源语法 `@achievement RARE_COURAGE { ... }` 不变；只是 JSON 字段名改了。这是唯一一处冲突——`ChoiceOption.id`（"opt_marry"）在 step 内部一层，不冲突。

## 实现责任分工

| Step 来源 | 谁注入 ID | 何时 |
|---|---|---|
| 原始 episode step | LS 编译器（[[entities/lunascripts]]） | 编译期，写入 `compiled.json` |
| Remix patch step | Backend `apply-patches.ts` | apply 时；LLM 不生成 ID |
| Forward plan patch step | 同上 | 同上 |

LLM 永远不生成 ID。它返回 id-less 的 IncomingPatch，apply-patches 在每次 apply 时**确定性**地 mint 一次。这意味着 patch 在 DB 里以 id-less 的 `IncomingPatch` 形态存（schema 用 `IncomingPatchSchema` 验），apply-patches 输出后才是 `InsertPatch` 形态（schema 用 `InsertPatchSchema` 验）。

## Engine 层改动

[[entities/lunaverse-backend]] 的 `app/core/cursor.ts` 和 `engine/cursor.ts` 双胞胎：

- `resolvePath(steps, path)`：从 `steps[N]` 改为 `findStepInContainer(steps, id)` ——逐项扫描，遇到 concurrent group 数组就深入找匹配 id 的 step
- `advanceSibling(root, path)`：以前是 `[..., last+1]` 纯路径运算；现在签名变成 `(root, path) → CursorPath | null`，需要查父容器结构才能知道下一个 sibling 是谁
- `popToParentSibling(root, path)`：剥所有连续的 escape segment 直到回到 stepID，再 advance 过去（含嵌套 `@else @if` 链）

Walker 和 StepPlayer 的算法结构不变，只是底层 helper 变了。视觉步 emit 时仍把 concurrent group 打包成 `Step[]` 输出（renderer 契约不变）。

## 一次性数据迁移

项目 test phase（无线上用户），cutover 一次到位：

1. **Recompile：**重新编译所有 LS 源 → 新的 `compiled.json` 带 IDs。Vendored fixture 和 OSS-hosted JSON 都需要刷新。
2. **Migrate state：**`scripts/migrate-step-ids.ts` 翻译 dev DB：
   - `Session.cursor`：用旧位置算法在新（带 ID）episode 里找到对应 step，读它的新 ID，写新 cursor
   - `Remix.anchorStepId`：同样翻译
   - `SessionPatch.patches[].anchor.stepId` + `replaceUntilStepId`：同样翻译
   - `SessionPatch.patches[].steps[]`：保持 id-less（apply-patches 每次 mint）
3. **Cutover：**部署新代码 + 跑 migration。Runtime 没有 dual-format 兼容路径——只懂新格式。

实际跑下来：11 sessions / 14 remixes / 29 session patches 干净迁移；20 个 patch 因 anchor 是 pre-spec 自由文本（如 `"dialogue_lishie_我也有礼物给你"`）被 drop（本来就 apply 不动）。

## 验收

- ~603 单测全绿，包含三条契约：lex sort = exec order、patch insert 不改原 step ID、`replace_until` 删 anchor 时 lookup miss
- E2E smoke：`scripts/smoke-stable-id-e2e.ts` 加载所有 dev session、应用 patches、走一次 walker，11/11 通过
- 迁移 dry-run 输出归档在 `docs/superpowers/2026-04-26-stable-step-id-migration.log`

## 解锁的能力

不只是修一个 bug——同时让一类 fragility 消失，进而解锁：

- **同 anchor 多 remix：**已经天然支持（patches 按 createdAt 排，patchSeq 区分）
- **patch-on-patch：**格式天然支持嵌套
- **`replace_until`：**变安全（fail-fast 而非静默）
- **跨集 patch 引用：**ID 是 episode-scoped 字符串，需要时可前缀 episodeId
- **Time-travel debug / replay：**给定 session + ID 可确定性 jump-resume
- **Admin 工具自解释：**`cursor=["0012_ch", "options", "opt_marry", "steps", "0003_dlg"]` 自带语义，旧 `[12, "options", 2, "steps", 3]` 没有

## 不做的

- **Episode 版本管理 / 源 LS 重排保护：**重排源 LS 后重编 → 已有 session 的 cursor 失效（IDs 是源序确定）。这是 episode versioning 问题，不是 cursor 问题，留给将来
- **Source LS 双向同步：**作者不需要看到 ID
- **CDN 缓存失效策略：**ops 关心，本设计不管
- **string compare 性能：**集合规模 negligible

## 关联

- [[concepts/ls-format]] —— Step JSON 现在每个都带 `id` 字段，type tag table 写在 `docs/JSON-OUTPUT.md §4.0`
- [[concepts/remix-anywhere]] —— Remix patch 走 `IncomingPatch` 写入 → `apply-patches` mint ID → 玩家加载时 `applyPatches` 重新 mint 同样的 IDs（确定性）
- [[entities/lunascripts]] —— 编译器在 `internal/emitter/emitter.go` 注入 IDs（`stepTypeTag` + `assignStepID` helpers）。frozen contract：算法一旦改动需要数据迁移
- [[entities/lunaverse-backend]] —— Engine 双胞胎、apply-patches、migration 脚本都在 backend
