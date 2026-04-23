---
title: Backend Support for MSS `@signal int`
tags: [moonshort, backend, mss, persistence]
sources: [raw/2026-04-23-signal-int-backend-design.md]
created: 2026-04-24
updated: 2026-04-24
---

# Backend Support for MSS `@signal int`

`@signal int` 是 MSS（MoonShort Script）在 2026-04-23 引入的第二种 `kind`——让剧本作者可以自由命名跨集持久的整数变量（计数器 / 阈值），例如"被 Easton 拒绝 3 次走 bad end"、"N 选 M 触发隐藏剧情"。本页描述 moonshort-backend 如何加载、持久化、求值这些作者变量。

## 核心设计原则：零人工介入

`@signal int` 是**纯脚本驱动机制**：

- **唯一写入路径**：MSS 指令经 walker → signal-executor → `writeInt`
- **唯一读取路径**：玩家推进到 `@if (name cmp N)` 时 `evalComparison` 从 `ctx.userInts` 取值
- **排查手段**：Postgres 直查 + `writeInt` 的保留名 warn 日志

后台**不暴露任何 HTTP 入口**去修改或读取作者变量（既不做 admin panel，也不做 cheat endpoint）。开 HTTP 入口会把 intSignals 框架成"被管理状态"，破坏"作者指令 → 引擎存 → @if 读"的契约。QA 想测阈值分支应该改脚本 fixture 或临时调 op 值，而不是开后门。

MSS 侧实现细节（lexer / parser / validator / emitter）见 [[concepts/mss-format]]；本页聚焦后台侧的契约与实现。

## MSS 输出契约

MSS `emitter` 生成如下 JSON 节点：

| 写入形态 | JSON |
|---|---|
| `@signal int x = 0` | `{"type":"signal","kind":"int","name":"x","op":"=","value":0}` |
| `@signal int x = -3` | `{"type":"signal","kind":"int","name":"x","op":"=","value":-3}` |
| `@signal int x +1` | `{"type":"signal","kind":"int","name":"x","op":"+","value":1}` |
| `@signal int x -2` | `{"type":"signal","kind":"int","name":"x","op":"-","value":2}` |

读取侧**复用现有 comparison AST**，不产生新 condition 类型：

```json
{
  "type": "comparison",
  "left": { "kind": "value", "name": "rejections" },
  "op": ">=",
  "right": 3
}
```

这意味着后端 Zod / TypeScript 只需扩展 `SignalStep`，condition 层零 AST 侵入。

## 语义（MSS spec §3）

- **跨集持久**：值在整个 playthrough 存活，与 `affection` / `mark` 同生命周期。
- **首次引用视为 0**：写侧 `+1` 之前从未赋值 → 从 0 起算，结果为 1；读侧 `@if (x >= 3)` 在任何写入前视为 0。
- **`=` 无条件覆盖**：每次执行都赋值；把 `@signal int x = 0` 放在 ep01 顶部、玩家回放该集会重置变量（作者责任，引擎不保护）。
- **`+N` / `-N` 中 N 必须非负**：负增量用 `-N` 形态表达；`+0` / `-0` 无意义（用 `= 0`）。MSS parser 和后端 Zod 两侧都校验。
- **命名空间与引擎数值共享**：裸名读取（`@if (x >= N)`）同一 path。作者不得与引擎保留名（`san`, `cha`, `atk`, `hp`, `xp`, `level`, 以及 novel 的 4 个 checking mssKey）冲突——MSS validator 上游拦截，后端 `writeInt` 防御性跳过保留名并 warn。

## 数据模型

### Prisma `Session`

Migration `20260423020000_session_int_signals`：

```prisma
model Session {
  // ...
  signals    Json @default("[]")   // 不变：string[]，mark 事件集合
  intSignals Json @default("{}")   // 新增：Record<string, number>
}
```

**为什么独立一列而不重塑 `signals`**：

- `signals: string[]` 和 `intSignals: Record<string,number>` 形状差得远，合并 JSON 只会让迁移和读取路径变复杂。
- 独立列 = 零数据迁移（所有历史 session 默认 `{}` = "未写过 int"）+ 独立回滚 + 两套服务逻辑互不牵扯。
- 和同期 gameConfig 改造（Session `san/attributes` 拆扁平列）正交推进。

## Schema 层：`app/core/schema.ts`

`SignalStepSchema` 改为判别联合：

```ts
const SignalMarkStepSchema = z.object({
  type: z.literal("signal"),
  kind: z.literal("mark"),
  event: z.string().min(1),
});

const SignalIntStepSchema = z
  .object({
    type: z.literal("signal"),
    kind: z.literal("int"),
    name: z.string().min(1).regex(/^[a-z][a-z0-9_]*$/, "must be snake_case lowercase"),
    op: z.enum(["=", "+", "-"]),
    value: z.number().int(),
  })
  .refine((s) => s.op === "=" || s.value >= 0, {
    message: "+/- ops require non-negative value",
    path: ["value"],
  });

const SignalStepSchema = z.discriminatedUnion("kind", [
  SignalMarkStepSchema,
  SignalIntStepSchema,
]);
```

`name` 的 snake_case 正则镜像 MSS validator，防止绕过 MSS 直接构造 JSON 注入非法名字。

## Type 层：`app/core/types.ts`

```ts
export interface SignalMarkStep { type: "signal"; kind: "mark"; event: string; }
export interface SignalIntStep  {
  type: "signal"; kind: "int";
  name: string; op: "=" | "+" | "-"; value: number;
}
export type SignalStep = SignalMarkStep | SignalIntStep;
```

### StateEffect

Walker / Executor 派发的 effect 联合：

```ts
export type StateEffect =
  | { kind: "affection"; character: string; delta: number }
  | { kind: "signal"; signalKind: "mark"; event: string }
  | { kind: "signal"; signalKind: "int"; name: string; op: "=" | "+" | "-"; value: number }
  | { kind: "butterfly"; description: string }
  | { kind: "achievement"; /* ... */ };
```

### ConditionEvalContext

```ts
export interface ConditionEvalContext {
  affection: Readonly<Record<string, number>>;
  signals: ReadonlySet<string>;

  /** 引擎管理数值（san/xp/level/各 checking mssKey）。严格：未知抛 UnknownAttributeError。 */
  values: Readonly<Record<string, number>>;

  /** 作者 @signal int 变量。宽松：未知默认 0（MSS spec §3.2）。 */
  userInts: Readonly<Record<string, number>>;

  /** engineValueNames = Object.keys(values) 的快照，用于 evalComparison 派发。 */
  engineValueNames: ReadonlySet<string>;

  lastChoices: Readonly<Record<string, "success" | "fail">>;
  lastCheckResult?: "success" | "fail";
  lastRating?: string;
  resolvedInfluences: Readonly<Record<string, boolean>>;
}
```

## 引擎侧求值：`app/core/condition.ts`

`evalComparison` 在处理 `left.kind === "value"` 时按 `engineValueNames` 派发：

```ts
if (ctx.engineValueNames.has(name)) {
  // 严格：未知 key 是引擎回归或 condition 书写错名
  const v = ctx.values[name];
  if (v === undefined) throw new UnknownAttributeError(name, Object.keys(ctx.values));
  leftValue = v;
} else {
  // 宽松：作者 @signal int 变量，首次引用默认 0
  leftValue = ctx.userInts[name] ?? 0;
}
```

**关键设计**：通过 `engineValueNames` 集合而不是"是否能在 values 里找到"来派发。这让我们同时：

- 保持**引擎 typo 检测**（把 `san` 写成 `sna` 仍然抛错）
- 支持 MSS spec 的 "first-time read = 0"（`rejections` 从未写过时视为 0，而非抛错）

代价：作者变量名 typo（`rejections` → `rejectons`）会静默返回 0，导致 `>= 3` 永远 false。在当前规模可接受，未来若需严格检测可由 novel-config-scan-service 扫出已声明的作者变量白名单。

## 引擎侧写入：`app/services/achievement/int-signal-service.ts`

```ts
export async function writeInt(
  tx: TxClient, ctx: SignalContext,
  name: string, op: "=" | "+" | "-", value: number,
): Promise<{ newValue: number; skipped: boolean }> {
  // 防御：作者绕过 MSS validator 用了引擎保留名 → warn + skip，绝不污染引擎字段
  if (ctx.evalCtx.engineValueNames.has(name)) {
    console.warn(`[signal-int] ignored write on engine-reserved name ${JSON.stringify(name)}...`);
    return { newValue: ctx.evalCtx.values[name] ?? 0, skipped: true };
  }

  const cur = ctx.intSignals[name] ?? 0;
  const next = op === "=" ? value : op === "+" ? cur + value : cur - value;
  ctx.intSignals[name] = next;

  await tx.session.update({
    where: { id: ctx.sessionId },
    data: { intSignals: ctx.intSignals },
  });

  // 同事务内 evalCtx.userInts 同步更新，使后续 condition 能读到当前累积值
  (ctx.evalCtx as { userInts: Record<string, number> }).userInts = {
    ...ctx.evalCtx.userInts, [name]: next,
  };

  return { newValue: next, skipped: false };
}
```

### 为什么 int 不参与 Path A 成就重评

`@signal mark` 的 Path A 会在每次 `writeMark` 后重评该 novel 的 manifest 成就（`reevaluateAfterMark`）。`@signal int` **不**触发——每个 `+1` 都重评会爆炸成本。int 变化对成就条件的影响延迟到下次 mark 或 ending 结算点重评，可接受。

### SignalContext 扩展

`app/services/achievement/types.ts`：

```ts
export interface SignalContext {
  userId: string; sessionId: string; novelId: string;
  currentEpisodeId: string;
  signals: string[];                    // mark 集合（就地 mutate）
  intSignals: Record<string, number>;   // 新增：作者 int 变量（就地 mutate）
  evalCtx: ConditionEvalContext;
}
```

### Walker + Executor

`app/core/walker.ts` 和 `app/core/executor.ts` 的 `signal` step case 按 kind 分派成对应 StateEffect：

```ts
case "signal":
  if (node.kind === "mark") {
    stateEffects.push({ kind: "signal", signalKind: "mark", event: node.event });
  } else {
    stateEffects.push({
      kind: "signal", signalKind: "int",
      name: node.name, op: node.op, value: node.value,
    });
  }
```

## save-service / save-action-service 集成

`applyEffects` 现在返回 `intSignals: ctx.intSignals`——`writeInt` 内部已经通过 `tx.session.update` 持久化，这个返回值供调用方在**跨集** overlay 内存 SessionRow：

```ts
const nextSessionState: SessionRow = {
  ...session,
  currentEpisodeId: next,
  affection: applied.affection as SessionRow["affection"],
  signals: applied.signals as SessionRow["signals"],
  intSignals: applied.intSignals as SessionRow["intSignals"],   // ← 本次新增
  butterflies: applied.butterflies as SessionRow["butterflies"],
  activeBuffs: [] as SessionRow["activeBuffs"],
};
```

没有这行，下一集的 `buildEvalCtx(nextSessionState)` 会读 `session.intSignals` 的旧快照，`@if (rejections >= 3)` 跨集连读会拿到错值。

### Replay 安全

`+/-` 操作**不幂等**——每次 replay 都会再累加。复用已有"synthetic replay 抑制 state effect 下发"通道（最近 commit `fix(play): suppress checkpoint enqueue during synthetic replay`），确保 replay 时不触发 writeInt。`=` 天然幂等，无论 replay 多少次结果一致。


## 为什么不做 admin / cheat 入口

2026-04-24 期间曾短暂落地了 `/admin/sessions` 面板 + `POST /api/admin/cheat/set-int-signal` + `GET /api/admin/cheat/status` 的 `intSignals` 回显，随后整体 revert（backend commits `833c2e8` / `4379be9` / `596aa02`），重新立为"零 HTTP 入口"原则。理由：

- **契约本质**：`@signal int` 的行为是"作者写 MSS 指令 → 引擎在玩家推进时执行 → `@if` 读取"，整条链路零人工介入是设计属性，不是遗漏。
- **admin panel 的心理模型错位**：呈现成"可查看 / 可编辑的 session 状态"会让 admin / 客服误以为应该盯着这些值 + 按需调整——可 intSignals 不是被管理状态，是剧本执行的中间产物。错误心理模型比没 UI 更糟。
- **cheat endpoint 是伪装的后门**：看起来只给 QA 跳阈值，实际是"任何 int 变量可被外部直接覆盖"的口子，和脚本驱动原则冲突。QA 想测分支应该改脚本 fixture 或临时调 op 值，不该开这个口。
- **mark signals 连带问题**：顺手做的 mark 编辑接口更危险——marks 绑定 Path A 成就重评，直接 PATCH 数组不跑 Path A 会造成状态不一致。

排查时的做法：Postgres 直查 `Session.intSignals`，以及利用 `writeInt` 保留名撞击时 console 里留的 warn 行。

## 测试覆盖

| 文件 | 覆盖面 | 测试数 |
|---|---|---|
| `__tests__/core/schema-signal-int.test.ts` | StepSchema 接受 `=/+/-`；拒 `+/-` 负值 / 浮点 / 非 snake_case 名；mark 回归 | 15 |
| `__tests__/core/condition-signal-int.test.ts` | evalComparison engine-vs-user 派发；混合 ctx；负值；保留名 engine 严格 + user 宽松 | 8 |
| `__tests__/services/achievement/int-signal-service.test.ts` | writeInt `=/+/-`；首次从 0 起步；累加；保留名 warn-skip；evalCtx 同步 | 10 |
| `__tests__/integration/signal-int-e2e.test.ts` | schema → walker → writeInt → condition 全链路；跨批次 cohesion | 7 |

合计 40 新测试；backend 总测 180 passed / 3 skipped。

## 已知非目标 / 未来扩展

- **Novel-scan 白名单**：如果要杜绝作者读变量 typo 静默返 0，需扩展 `novel-config-scan-service` 收集每本小说用到的 `@signal int` 名字集合并在 condition eval 里校验。当前未实现。
- **Path A 覆盖 int**：int 变化触发的成就目前靠下一次 mark / ending 重评。如果实测需要更低延迟，需引入 `reevaluateAfterInt` 或类似钩子。
- **`@signal float` / `@signal string`**：MSS spec 留白但未实现；当前剧情机制不需要。

## 相关页面

- [[concepts/mss-format]] — MSS 语法与 `@signal int` 在脚本侧的定义
- [[concepts/novel-game-config]] — 引擎保留名名单来源（per-novel `mssKey`）
- [[entities/moonshort-backend]] — 整个后端概览
