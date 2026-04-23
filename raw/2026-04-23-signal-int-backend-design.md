# Backend 支持 `@signal int` —— 设计文档

**日期**：2026-04-23
**作者**：cdotlock + Claude
**状态**：Draft（实施中）
**关联**：
- MSS 侧已 landed：`../../moonshort-script/docs/superpowers/specs/2026-04-23-signal-int-design.md`
- 前置改造：`2026-04-23-novel-game-config-design.md`（gameConfig，已并入主线）

---

## 1. 背景

### 1.1 MSS 侧已落地

`moonshort-script` 仓库 20 个 commit 已 merged：

- AST：`SignalNode` 扩展 `Name / Op / Value` 字段，`SignalKindInt = "int"`
- Parser：三种写入形态（`= <int>` / `+<N>` / `-<N>`），含 `+0` / 浮点 / 浮点样式拒收
- Validator：保留名单（`san, cha, atk, hp, xp, dex, int, str, wis, con`）拦截作者命名冲突
- Emitter：`{"type":"signal","kind":"int","name":"...","op":"=|+|-","value":N}`
- 读取：复用 comparison AST（`left.kind="value"`），**不产生新 condition 类型**
- Golden：`testdata/feature_parade/stress_output.json` 含 `stress_count` 完整用例

后台目前对该 JSON 形态：**Zod 校验失败**（`SignalStepSchema` 只放 `kind: "mark"`），直接阻断 Episode 加载。

### 1.2 目标

让后台能**加载 → 持久化 → 读取 → 重放**作者自定义整数变量，契合 MSS spec §3 的全部语义：

- 跨集持久（与 `affection` / `mark` 同生命周期）
- `=` 无条件赋值；`+/-` 增量（N 非负）
- **首次引用视为 0**（写、读两侧都要满足）
- 命名空间与引擎数值共享，保留名冲突由 MSS validator 上游拦截（后台做 defensive log）
- Replay 安全：`+/-` 非幂等，必须走已有"synthetic replay 抑制 state effect"通道

### 1.3 非目标

- **不改 MSS 契约**：完全按它已发的 JSON 格式消费
- **不做 admin 可视化编辑**：cheat endpoint 供 QA/作者调试足矣
- **不做典型化校验**（validator 级别的"作者使用了未声明的 int"）——MVP 靠 MSS validator + 默认 0 语义

---

## 2. 数据模型变更

### 2.1 Prisma `Session`

```prisma
model Session {
  // ... 现有字段
  signals    Json @default("[]")      // 不变：string[]，存 mark 事件
  intSignals Json @default("{}")      // 新增：Record<string, number>
}
```

**设计要点：**

- **独立一列**，不重塑 `signals`：迁移面小、回滚容易、与 mark 完全正交
- 默认 `{}`，老 session 天然向后兼容
- 形状：扁平 `{"rejections": 3, "brave_count": 2}`——扫描、调试、回填皆简单

### 2.2 迁移

```sql
ALTER TABLE "Session" ADD COLUMN "intSignals" JSONB NOT NULL DEFAULT '{}';
```

无数据回填（新字段默认值 `{}`，所有历史 session 自动 = "未写过任何 int"）。

---

## 3. Schema 层（`app/core/schema.ts`）

### 3.1 `SignalStepSchema` 判别联合

```ts
const SignalMarkStepSchema = z.object({
  type: z.literal("signal"),
  kind: z.literal("mark"),
  event: z.string().min(1),
});

const SignalIntStepSchema = z.object({
  type: z.literal("signal"),
  kind: z.literal("int"),
  name: z.string().min(1).regex(/^[a-z][a-z0-9_]*$/, "must be snake_case"),
  op: z.enum(["=", "+", "-"]),
  value: z.number().int(),
}).refine(
  (s) => !(s.op !== "=" && s.value < 0),
  { message: "+/- op requires non-negative value (use op='=' for negative assignment)" },
);

const SignalStepSchema = z.discriminatedUnion("kind", [
  SignalMarkStepSchema,
  SignalIntStepSchema,
]);
```

顶层 `StepSchema` 的 union 不动——`z.discriminatedUnion` 对 `union([..., SignalStepSchema, ...])` 透明。

### 3.2 Condition（comparison）

**不改**。`left.kind="value"` + `name: string` 已覆盖 `@signal int` 读取 AST。

---

## 4. Type 层（`app/core/types.ts`）

### 4.1 `Step` 类型

TS 层对 `SignalStep` 拆分判别联合（mirror schema）：

```ts
export type SignalMarkStep = { type: "signal"; kind: "mark"; event: string };
export type SignalIntStep  = { type: "signal"; kind: "int"; name: string; op: "=" | "+" | "-"; value: number };
export type SignalStep = SignalMarkStep | SignalIntStep;
```

### 4.2 `StateEffect`

```ts
export type StateEffect =
  | { kind: "affection"; character: string; delta: number }
  | { kind: "signal"; signalKind: "mark"; event: string }
  | { kind: "signal"; signalKind: "int"; name: string; op: "=" | "+" | "-"; value: number }  // NEW
  | { kind: "achievement"; /* ... */ }
  | { kind: "butterfly"; description: string };
```

### 4.3 `ConditionEvalContext`

新增两个字段：

```ts
export interface ConditionEvalContext {
  // ... 现有
  values: Record<string, number>;          // 引擎管理数值（strict：未知抛错）
  userInts: Record<string, number>;        // NEW：作者 int 变量（宽松：未知默认 0）
  engineValueNames: ReadonlySet<string>;   // NEW：引擎保留名单快照，用于 eval 分派
}
```

---

## 5. 引擎侧改造

### 5.1 `buildEvalCtx`（`app/services/save-service.ts`）

```ts
const values: Record<string, number> = {
  ...attributes,
  [cfg.variables.continuous.mssKey.toLowerCase()]: session.continuousVariable,
  san: session.continuousVariable,
  xp: session.xp,
  level: session.level,
};
const engineValueNames = new Set(Object.keys(values));
const userInts = (session.intSignals as Record<string, number>) ?? {};

return {
  affection,
  signals,
  values,
  userInts,
  engineValueNames,
  // ...
};
```

### 5.2 `evalComparison`（`app/core/condition.ts`）

```ts
function evalComparison(cond: ComparisonCondition, ctx: ConditionEvalContext): boolean {
  let leftValue: number;
  if (cond.left.kind === "affection") {
    leftValue = ctx.affection[cond.left.char] ?? 0;
  } else {
    const name = cond.left.name;
    if (ctx.engineValueNames.has(name)) {
      // 引擎管理值：严格。未知就是引擎回归
      const v = ctx.values[name];
      if (v === undefined) {
        throw new UnknownAttributeError(name, Object.keys(ctx.values));
      }
      leftValue = v;
    } else {
      // 作者 @signal int 变量：宽松，首次引用视为 0（MSS spec §3.2）
      leftValue = ctx.userInts[name] ?? 0;
    }
  }
  // ... 操作符 switch 不变
}
```

**关键**：用 `engineValueNames` 集合做派发，保留现有"引擎名字 typo 抛错"的防线——只有当名字**不属于**引擎集合时才走默认 0 fallback。

### 5.3 Walker（`app/core/walker.ts:109`）+ Executor（`app/core/executor.ts:136`）

两处 `stateEffects.push` 扩展为按 kind 分派：

```ts
// walker.ts
if (node.kind === "mark") {
  stateEffects.push({ kind: "signal", signalKind: "mark", event: node.event });
} else if (node.kind === "int") {
  stateEffects.push({ kind: "signal", signalKind: "int", name: node.name, op: node.op, value: node.value });
}
```

（Executor 的 `applyCgSubStep` 同形改造。）

### 5.4 `SignalExecutor`（`app/services/achievement/signal-executor.ts`）

```ts
for (const eff of effects) {
  if (eff.kind === "signal" && eff.signalKind === "mark") {
    const res = await writeMark(tx, ctx, eff.event);
    if (res.added) newSignals.push(eff.event);
    unlocked.push(...res.unlocked);
  } else if (eff.kind === "signal" && eff.signalKind === "int") {
    await writeInt(tx, ctx, eff.name, eff.op, eff.value);   // NEW，不参与 Path A（int 不触发成就）
  } else if (eff.kind === "achievement") {
    // ...
  }
}
```

### 5.5 `writeInt`（新文件：`app/services/achievement/int-signal-service.ts`）

```ts
export async function writeInt(
  tx: TxClient,
  ctx: SignalContext,
  name: string,
  op: "=" | "+" | "-",
  value: number,
): Promise<{ newValue: number }> {
  // Defensive：作者若绕过 MSS validator 用了引擎保留名，log warn 并跳过
  if (ctx.evalCtx.engineValueNames.has(name)) {
    console.warn(`[signal-int] skipped write on engine-reserved name: ${name}`);
    return { newValue: ctx.evalCtx.values[name] ?? 0 };
  }

  const cur = ctx.intSignals[name] ?? 0;
  const next = op === "=" ? value : op === "+" ? cur + value : cur - value;

  ctx.intSignals[name] = next;

  await tx.session.update({
    where: { id: ctx.sessionId },
    data: { intSignals: ctx.intSignals },
  });

  // 同事务内同步 evalCtx，供后续 condition 读到最新值
  (ctx.evalCtx as { userInts: Record<string, number> }).userInts = {
    ...ctx.evalCtx.userInts,
    [name]: next,
  };

  return { newValue: next };
}
```

**`SignalContext` 扩展** `intSignals: Record<string, number>`——和现有 `ctx.signals: string[]` 并列；由 save-service 在 fold 阶段注入。

### 5.6 Save-service fold

`save-service` 当前对 effects 的 fold 逻辑里，`signal mark` 已经 fold 到 `session.signals`。新加 `signal int` 的 fold——但因为 `writeInt` 内部已经 `tx.session.update`，fold 层**不需要再额外操作**，只要 `SignalContext` 带上 `intSignals` 的引用即可。

### 5.7 Replay 安全

复用现有机制：`synthetic replay` 抑制 state effect 下发（参见最近 commit `fix(play): suppress checkpoint enqueue during synthetic replay`）。具体实现不改——测试重点验证 `@signal int x +1` 在重放时**不会累加**。

---

## 6. Admin 接口

### 6.1 Cheat endpoint：`POST /api/admin/cheat/set-int-signal`

```ts
// body: { sessionId, name, value }
// 直接写入 session.intSignals[name] = value，绕过 walker/executor
```

用于 QA 快速跳到某 int 阈值（比如 `rejections=3` 直接测 bad end 分支）。对标现有 `/api/admin/cheat/set-signal`（mark）。

### 6.2 Admin UI 展示

在**已有** session 详情/调试面板里加一行："**作者变量**"，只读表格展示 `session.intSignals`。新文件不开；和现有面板同文件加小段即可。

---

## 7. 防御策略

| 风险 | 防线 | 备注 |
|------|------|------|
| 作者用了引擎保留名 | MSS validator 上游拦截 | 后台不镜像名单 |
| 后台仍收到保留名写入（MSS bug / cheat 接口手写） | `writeInt` log warn + skip | 绝不污染引擎字段 |
| condition 左值 typo | `engineValueNames` 命中抛错；作者名字默认 0 | 短期可接受，长期可加 novel-scan 生成 "known author ints" 集做更严格校验 |
| Replay 重复写 | 复用现有 replay-suppression | 测试覆盖 |
| `+/-` 溢出 | JS number 精度 `2^53`；`Int` 列存 number 足够 | YAGNI，不做上限 |

---

## 8. 代码落点汇总

| 文件 | 改动 |
|------|------|
| `prisma/schema.prisma` | +`intSignals Json @default("{}")` |
| `prisma/migrations/.../migration.sql` | ADD COLUMN |
| `app/core/schema.ts` | SignalStepSchema 拆判别联合 |
| `app/core/types.ts` | SignalStep / StateEffect / ConditionEvalContext 扩展 |
| `app/core/condition.ts` | `evalComparison` 加 engine-vs-user 分派 |
| `app/core/walker.ts` | signal 节点按 kind 分派 effect |
| `app/core/executor.ts` | `applyCgSubStep` 同上 |
| `app/services/save-service.ts` | `buildEvalCtx` 注入 `userInts` + `engineValueNames`；fold 传 `intSignals` 到 SignalContext |
| `app/services/achievement/signal-executor.ts` | `eff.signalKind === "int"` 分支 |
| `app/services/achievement/int-signal-service.ts`（新） | `writeInt` |
| `app/services/achievement/types.ts` | `SignalContext` +`intSignals` |
| `app/api/admin/cheat/set-int-signal/route.ts`（新） | cheat |
| `app/admin/sessions/[id]/page.tsx`（已存在） | 只读展示 intSignals |

---

## 9. 测试计划

### 9.1 单测

- `schema.test.ts`：
  - 接受 `{kind:"int", name:"x", op:"=", value:0}` / `{op:"+",value:1}` / `{op:"-",value:2}` / `{op:"=",value:-3}`
  - 拒收 `{op:"+", value:-1}` / 非 snake_case 名 / 缺字段
  - 回归：`{kind:"mark", event:"X"}` 仍通过
- `condition.test.ts`：
  - `engineValueNames` 命中 + `values` 有 → 正常
  - `engineValueNames` 命中 + `values` 缺 → throw（引擎回归检测）
  - 未命中 `engineValueNames` + `userInts` 有 → 返回值
  - 未命中 + `userInts` 无 → 默认 0（不 throw）
- `int-signal-service.test.ts`：
  - `=` 覆盖（含负值）
  - `+` / `-` 累加（首次从 0 起算）
  - 保留名写入被跳过 + warn 触发
  - 同事务 evalCtx.userInts 即时更新

### 9.2 集成测

- MSS golden JSON（来自 `feature_parade/stress_output.json`）端到端加载 + 运行
- 序列：`@signal int x = 0` → `@signal int x +2` → `@if (x >= 2)` 命中 → `@signal int x -1` → `@if (x >= 2)` 不命中
- Replay：同一 choice 回退再前进，int 值不重复累加

### 9.3 Cheat endpoint 测试

- `POST /api/admin/cheat/set-int-signal` 直接写 session.intSignals
- 写后下次 condition eval 用到新值

---

## 10. 实施阶段

| 阶段 | 内容 | 预估 |
|------|------|------|
| **1** | Prisma migration + Zod schema + Type 层 | 0.3 天 |
| **2** | Walker / Executor / SignalExecutor / writeInt | 0.5 天 |
| **3** | buildEvalCtx + evalComparison + 单测 | 0.3 天 |
| **4** | Cheat endpoint + Admin UI 展示 | 0.3 天 |
| **5** | 集成测 + MSS golden 接入 | 0.4 天 |
| **6** | 回归全跑 + wiki_ingest | 0.2 天 |
| **合计** | | **~2 天** |

每阶段一个原子 commit（或一组密切相关的小 commit），逐步推 origin/main。

---

## 11. 决策记录

### 11.1 为什么新增独立列而非重塑 `signals`

- `signals: string[]` 和 `intSignals: Record<string,number>` 形状差得远，强行合并 JSON 只会让迁移和读取都变麻烦
- 独立列 = 零迁移 + 独立回滚 + 两套服务逻辑互不牵扯

### 11.2 为什么读路径不引入新 condition 类型

- MSS 已决定"读取复用 comparison"——后台硬加 `userIntCondition` 等于破坏契约
- `engineValueNames` 派发足够区分两类 value，零 AST 侵入

### 11.3 为什么未知作者名默认 0 而非 throw

- MSS spec §3.2 明文"首次引用视为 0"——契约
- 作者 typo 的代价：返回 0（可能导致 `>= 3` 永远 false），比起 throw 让整个 session 崩溃，失败模式更温和
- 长期可由 novel-scan 补强：收集所有 `@signal int` 名字形成白名单，白名单外才 throw

### 11.4 为什么 int signal 不参与 Path A（成就重评）

- 成就触发条件的左值里，`@signal int` 变量是被支持的——但**重评时机**挂在 mark 写入（Path A 已有设计）
- int 变化触发成就重评会爆炸（每个 `+1` 都重评一遍）；改成"每个 step 后重评"超出本次范围
- 现状：int 变量影响的成就在下次 mark / episode 结算点被重评，延迟几步可接受
- 未来需要再议

---

## 12. 未决问题

1. **Path A 覆盖**：int 变化触发的成就条件，靠下次 mark / ending 时重评——这个延迟对游戏体验是否可接受？（目前 YAGNI，等有实际成就定义再看）
2. **Novel scan 扩展**：是否要把每本小说用到的 `@signal int` 名字收集进 `novel.gameConfig.knownInts`，供后台白名单校验？（当前不做，追踪到第二期）
3. **Admin UI 深度**：除了只读展示，要不要加"人工编辑 + 保存"按钮？（当前 cheat endpoint 足够）
