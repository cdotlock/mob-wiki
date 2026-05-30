---
title: Dream bonus_only OP + Feed Skip-to-E1
tags: [dreaming, dream-agent, entry-patch, backend]
sources: [raw/2026-05-30-dream-bonus-only-and-feed-skip-design.md]
created: 2026-05-30
updated: 2026-05-30
---

2026-05-25 brainstorm → 2026-05-26+ 落地：dream entry-patch 从 3 个 v1 ops (`choice_add_option` / `choice_replace_option` / `replace_gate`) 全部废掉，换成单一新 op **`bonus_only`** — terminal placement + template "Continue" 选项 + LLM 写的 dream 选项文案 + 机械路由。同时改 home feed 入口：点 dream 卡直接落 dream E1，不再走一遍 source 集 + auto-pick。源 spec：[`docs/superpowers/specs/2026-05-25-dream-bonus-only-and-feed-skip-design.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/superpowers/specs/2026-05-25-dream-bonus-only-and-feed-skip-design.md)。详见 [[concepts/dreaming-universe]]。

## 为什么换

三个 v1 ops 的实际症状：planner + entry-patch specialist 原本应该默认走最温和的 `choice_add_option`（在已有 choice 末尾追加 ✦ dream 选项，不改原文案），但生产里另外两个 op 仍在被 emit，玩家 UX 不一致 + 事后 QA 噪声大。

Feed 入口的浪费：overlay 的 `entryEpisodeId` 是 **source 集** 而不是 dream E1，玩家点卡进游戏要靠 player 端 auto-pick 走完一整集才到 dream 选项。新结构规则下入口已经是 source 集最后一拍，再播一遍纯属浪费。

## bonus_only Wire Shape

```jsonc
{
  "op": "bonus_only",
  "optionFlavor": "Step through the silvered mirror."
}
```

只有两个字段。没有 `anchor` / `choiceStepId` / `routes` — applier 自己从 source 集 metadata 推。`optionFlavor` 是唯一 LLM 出力的字段（≤120 字 + Zod `min(1).max(120)`）。

`EntryPatchStorageSchema.operations[]` 必须**恰好一个**元素：`.refine` 强制 if any op is `bonus_only`, length == 1，其他 op 全拒。一个 source 集只有一个 terminal gate，多个 `bonus_only` 会冲突在同一锚点。

设计意图：`bonus_only` 整个结构意图都是机械的（"在 source EP N 末尾挂一个 Continue/Dream coda"），唯一的创作自由度是 dream 选项文案钩子。其他都是噪声。

## Applier 机制

给定一个 source 集，其 top-level gate 是简单 fallback `{ next: <source EP N+1> }`（runtime EpisodeJSON 里 `gate` / `ending` 是 top-level XOR 字段；接下集的 source 集就是 `ending: null` + `gate.next`），applier 做两件事：

1. 在 `steps[]` 末尾追加一个合成 `choice` step，**恰好两个选项**：
   - **Option A**: `{ mode: "safe", text: "<i18n: dream.bonus.continueOption>", steps: [] }` — 固定 i18n template，所有 dream 共用一份本地化文案
   - **Option B**: `{ mode: "safe", text: <optionFlavor>, steps: [], _dreamSource: { kind: "dream_entry", assignmentId, dreamId } }` — LLM 写的文案 + 同样的 `_dreamSource` tag（player UI 的 ✦ dream pill 渲染不变）
2. 重写 terminal gate：
   ```
   { if:   { type: "choice", option: <B-id>, result: "any" },
     next: "dream/<dreamId>:01",
     else: <original gate.next>  // source EP N+1
   }
   ```

两个选项 `steps[]` 都空，唯一区别是 gate 路由到哪。这保证 Option A 对主线"零修改"。

## Planner Preflight

planner 必须 reject 不符的 source 集，否则报：

| 检查 | 失败 kind |
|---|---|
| 必须有 terminal fallback `gate: { next: <id> }`（复杂 `if` gate 不行） | `dream_bonus_only_no_terminal_gate` |
| 必须有下一集（source-branch terminal 集不行） | `dream_bonus_only_no_next_episode` |
| 复杂 gate | `dream_bonus_only_complex_gate` |
| `returnToMain.targetEpisodeId` 必须等于 Continue 分支的 `gate.next` 目标 | `dream_bonus_only_gate_target_mismatch` |

错误 surface 走和已有 planner violation 一样的 `fixHint` shape。

## No-Mainline-Mutation Invariant（bonus_only 核心）

`bonus_only` dream **禁止**任何主线持久 state 改动。dream MSS 源不能 emit：

- `@affection <character> <delta>`
- `@signal mark <event>` / `@signal int <name> <op> <value>`
- `@butterfly <description>`
- `@achievement <id>`

理由：`bonus_only` 是个 coda。原本选 "Continue" 的观众必须拿到 byte-identical 的主线体验（玩家从来没有 Dream assignment 一样）。dream branch 通过自己的 ending gate 回 source EP N+1 时，那些 mutation 会泄漏进 post-dream 主线 state。

允许的 step（不动主线 persistence）：`dialogue` / `narrator` / `you` / `bubble` / `bg` / `char` / `cg` / `music` / `sfx` / `phone` / `text_message` / `choice` / `minigame` / `trick` / `pause` / `if` / `label` / `goto`。dream 内 `@if` / `@label` / `@goto` 都是 local 不持久。

**三层 defense-in-depth**：

| 层 | 位置 | kind |
|---|---|---|
| Writer prompt | `services/dream-agent/prompts/dream_agent__writer__system.md` — Iron Rule 明确禁止四个命令 + pre-commit checklist | — |
| Reviewer prompt | `services/dream-agent/prompts/dream_agent__writer__reviewer__system.md` — mandatory check + violation kind | `dream_mainline_mutation_forbidden` |
| Backend validation | `services/dream-agent/src/validation.ts` — content-walk 扫每个 dream-episode MSS step `type`，拒 `affection` / `signal` / `butterfly` / `achievement` | `dream_mainline_mutation_forbidden` (severity: `critical`) |

## 关闭旧 ops 的两道闸（write side）

**验证侧 + 生成侧都要**：validation 是 fail-loud 网（接 agent bug），生成侧是 fail-quiet 网（不浪费 token）。两层在位，单层 regression 不会泄漏旧 op 到落库 dream。

### 验证侧 — `app/core/episode-overlay/operation-schema.ts`

1. 新增 `BonusOnlyOpSchema` 作为 `DreamEntryOperationSchema` discriminated union 第四 variant（schema 仍能 parse 旧 op 做 read back-compat）
2. 新增 export `ALLOWED_DREAM_OPS = new Set(["bonus_only"])` + `WritableDreamEntryOperationSchema`（裹 `DreamEntryOperationSchema` 用 `.refine` 拒任何 ALLOWED 外的 op，message `"op X is disabled in this build"`）
3. `EntryPatchStorageSchema`（`app/services/dream-entry-patch-schema.ts`）把 `DreamEntryOperationArraySchema` 换成 writable 变体 → 同步堵 admin-inject endpoint + 生产 checkpoint endpoint
4. Read paths（`dream-readonly-service`、dream presence overlay loaders）继续用旧 schema 能 parse 残留；但 §7 cleanup 后应该是 0 条

### 生成侧 — `services/dream-agent`

```ts
// before
const ALLOWED_ENTRY_PATCH_OPS = new Set(["choice_add_option", "choice_replace_option", "replace_gate"]);
// after
const ALLOWED_ENTRY_PATCH_OPS = new Set(["bonus_only"]);
```

Prompts 同步：
- `dream_agent__entry_patch__system.md` — 删掉旧 op 所有引用（Op Reference、examples、common-failure rows），**不留** "disabled — do not emit" 注释（用户反馈：留旧 shape 在 prompt 反而诱导 LLM 高压时往里 rationalize）；改写成单 section 描述 `bonus_only` wire shape + flavor tone-guidance + "the applier does the rest"
- `dream_agent__planner__system.md` — `sourceEntry.op` enum 改成 `["bonus_only"]`；新 preflight 规则文档化；删旧 op 选型 guidance；`anchorHint` / `anchorStepId` / `choiceStepId` / `optionId` 字段保留 optional/nullable（不破坏 fixture），文档化为 "ignored for bonus_only"；entry-patch specialist 不 call `find_anchor_by_query`（prompt-side no-op，不删工具，legacy debug 不受影响）

## Feed Skip-to-E1（read side）

行为改动全在 `app/services/dream-replay-service.ts` 的 `createReplaySession`：

```ts
const opType = readBonusOnlyOrLegacy(dream.entryPatch);
// "bonus_only" → 直接进 dream E1
// "legacy"     → fall through 到旧 source-ep + auto-pick 路径

const startEpisodeId =
  opType === "bonus_only"
    ? firstDreamEpisodeId(dream)   // dream.episodeIds[0]
    : dream.entryEpisodeId;        // 旧行为
```

`readBonusOnlyOrLegacy` 用 legacy-tolerant `EntryPatchStorageSchema`（read 不走 allowlist refine）parse，看 `operations[0].op`：`bonus_only` 走新路径，其他都按 legacy 兜底。Cleanup 后预期 0 legacy dream，但 path 保留作防御。

**特意不删** `app/(player)/play/[sessionId]/page.tsx` 的 auto-pick effect + `dream-source-detection` helper（用户偏好）— 给 cleanup 后残留 dream 兜底。对 bonus_only dream 而言，transient session 进 `dream/<id>:01` 第一步是 narration，不是 choice，auto-pick 的 `decision.kind !== "choice"` guard 直接 bail，路径走到但不动。

## Legacy Dream 一次性清理

`scripts/cleanup-legacy-dream-ops.ts`，默认 dry-run；`--apply` 实跑。

Detection：JS 侧 findMany 后扫 `entryPatch.operations` 数组里有没有任何元素 `op ∈ {choice_add_option, choice_replace_option, replace_gate}`（避免 JSON-path SQL 跨 DB 不兼容）。

每条命中 Dream：
1. 删指向它的 `DreamAssignment`
2. Null out 被删 assignment 的 `Session.dreamReplayAssignmentId`（防御性）
3. 走 `deleteSessionGraph` 清孤儿 transient session
4. 删 Dream 行

Dry-run 输出：Dream / Assignment / transient session 删除数，by-novel 表。

**Rollout 序**：先 ship §5 的两道闸（保证瞬间起没有新 legacy dream 落库），再跑 cleanup；Feed-skip §6 可同步 / 滞后 ship，independent。**脚本本身在一次成功 apply 后必须从 main 删掉** — 留在 tree 是脚类弹药。

## 测试覆盖

| Layer | 文件 | Case |
|---|---|---|
| Wire schema | `__tests__/core/episode-overlay/...` | `WritableDreamEntryOperationSchema` 接 `bonus_only` / 拒 3 legacy（带预期 error message）；round-trip `bonus_only` → applier → re-stringify 保留 `optionFlavor` + 生成期望 choice step + gate |
| Applier integration | `__tests__/core/episode-overlay/apply-overlays.*.test.ts` | fixture source 集（简单 fallback gate 路由 `n-x/ep-006`）apply `bonus_only` 出期望 post-overlay steps[] + gate AST |
| dream-agent validation | `services/dream-agent/__tests__/` | `validation.ts` 拒 `sourceEntry.op !== "bonus_only"` 的 plan；preflight 拒没 `@ending` step 或没 next episode 的 source |
| Replay service | `__tests__/services/dream-replay-service.test.ts` | bonus_only entryPatch → `currentEpisodeId === dream.episodeIds[0]`；保留 legacy case 锁兜底 |
| Smoke | `scripts/seed-and-tag-mock-dreams.ts` + companion | seed 一条 bonus_only dream 端到端，home feed 上有，点入直接落 dream E1，完成 → 回 source EP N+1 |

## Non-goals

- **Dream ending 语义不变**：`returnToMain.targetEpisodeId` 必等 source EP N+1（planner-preflight 校 + terminal-policy gate 强制），Writer Iron Rule 3（"never use `@ending` on the final Dream episode"）不动
- 三个旧 ops 的 applier dispatch **保留在代码**做防御 fallback；只有生产 write 路径被关
- dream 内容 authorship / op 选择以外的 planning / entry-patch 外其他 dream-agent prompt 都不动
- admin-only inject / preview endpoint 仍能 read 旧 payload（只写边界拒）

## 相关

- [[concepts/dreaming-universe]] — 父系统，bonus_only 是 entry-patch 的新唯一 op
- [[concepts/villain-season-demo]] — 第一本生产环境 bonus_only 真用例
- [[concepts/remix-anywhere]] — Dream entry 和 Remix 共存的 step ID 锚点契约
