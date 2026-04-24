---
title: Remix Anywhere — Player Intervention via D20+DC Patch Injection
tags: [moonshort, backend, remix, llm, mss, tabletop]
sources: [docs/superpowers/specs/2026-04-24-remix-anywhere-design.md]
created: 2026-04-25
updated: 2026-04-25
---

# Remix Anywhere

Remix Anywhere 是 moonshort-backend 在 2026-04-24 上线的核心玩家介入系统。玩家在播剧时可以**长按任意对白**或**点击角色立绘**，输入一段 ≤50 字的自由文本（如"抓住她的手"、"告诉他你说谎了"），由跑团式 D20 + DC 机制决定是否成功，成功则把 LLM 生成的一小段剧情（3-8 个 MSS step）直接 splice 进当前集，并在后续 3 集异步生成"回响"。

和旧的 [[entities/moonshort-backend#drama-remix]] 系统（重新生成整集）根本不同：本系统**不生成新剧集**，只在现有剧本里插入小段 InsertPatch，写作成本 10%、叙事一致性强、延展性极好。

## 设计哲学

1. **不生成新剧集**——旧的 Drama Remix（M7）通过 dramatizer 生成完整替代集，成本高延迟长；Remix Anywhere 在现有集里 splice 3-8 步 MSS，用既有 walker 消费。
2. **服务器 authoritative 的 D20 预投骰**——`/remix/submit` 时服务器就用 `checkDC({attrValue, dc})` 决出胜负，客户端 `DiceModal` 只是播 ~1.5s 动画，反作弊天然成立。
3. **失败点永久锁定是灵魂**——DC 失败后 `(episodeId, stepId)` 写入 `Session.failedRemixPoints`，该玩家永远无法再 remix 这个点。防止玩家"试到成功为止"。
4. **Walker 单通道消费 patch**——patch 里的 `@signal` / `@butterfly` / `@affection` 不在 commit 时直写 session，而是玩家 **walk 到那一步**时由既有 foldStateEffects 自然写入。消除双写路径、保证 int 增量不会被扣两次。
5. **Forward planner 的"回响不是重演"**——Remix 成功后异步在未来 3 集生成短 patch（2-6 步），让角色**回响**这次介入（"她那晚说的话还在耳边"），而非复述事件。把玩家介入变成持久叙事历史。
6. **Module boundary 预埋拆服务**——`app/services/remix/*` 被 ESLint 强制隔离，只能通过 `main-backend-client.ts` facade 访问主后端。将来拆独立进程时只改 facade 一个文件。

## 服务拓扑

```
┌─────────────┐        ┌──────────────────────────────────────┐
│   Browser   │◄───────│      Next.js 16 (App Router)         │
│  /play page │        │      单进程                          │
│  RemixProvider       │                                      │
└──────┬──────┘        │  /api/remix/* route handlers         │
       │               │    submit / commit / drain           │
       │ HTTP          │    session-patches / status          │
       │               │                                      │
       ▼               │  app/services/remix/*                │
       ·               │    remix-service (orchestration)     │
       ·               │    prescreen / sync2 / fail /        │
       ·               │       forward-planner LLM            │
       ·               │    apply-patches, dice, failed-point │
       ·               │    main-backend-client (facade)      │
       ·               └──┬───────────┬──────────────┬────────┘
       ·                  │ prisma    │ outbox       │ LLM
       ·                  ▼           ▼              ▼
       ·             ┌──────────┐ ┌────────┐  ┌────────────┐
       ·             │PostgreSQL│ │ Redis  │  │ Langfuse + │
       ·             │  :5433   │ │ :6379  │  │ OpenAI 上游 │
       ·             └──────────┘ └────▲───┘  └────────────┘
       ·                               │
       ·                               │ BullMQ worker
       ·                               │ (workers/queue-worker.ts)
       ·                               └───────────────────
```

**进程布局**：

| 进程 | 职责 |
|---|---|
| Next dev server (`pnpm dev`) | 全部 HTTP API + SSR |
| BullMQ worker (`pnpm worker:dev`) | 消费 `OutboxEvent`，执行 `remix.sync2` + `remix.forward_plan` 任务 |
| Postgres | Session / Remix / RemixForwardPlan / SessionPatch / OutboxEvent |
| Redis | BullMQ backing store + dispatcher locks |

**Main Backend vs Remix Service 边界**：

当前两部分在同一 Next 进程，但 `app/services/remix/*` 被 ESLint 规则强制隔离，不能直接 import `save-service` / `episode-service` / `game-config`。唯一通道是 `app/services/remix/main-backend-client.ts` facade：

```typescript
loadSession(sessionId, userId)
loadEpisodeBundle(novelId, episodeId, language?)
listEpisodesInSeqRange(novelId, startSeq, endSeq)
getNovelGameConfig(novelId)
sessionAttributes(session, cfg)
characterSettings(characterIds)
spendGemsForRemix(userId, amount, remixId, sessionId)  // idempotent by remixId
```

## 核心 Service 层

| 模块 | 职责 | 纯度 |
|---|---|---|
| `types.ts` | `InsertPatch` / `PatchAllowedStep` / `ButterflyRecord` / `FailedPointRecord` 类型 | TS-only |
| `patch-schema.ts` | Zod schema。`InsertPatchSchema` 是 patch 白名单的权威（mirror MSS 排除 choice/gate/minigame/...） | 纯 |
| `dice-service.ts` | `preRoll({attrValue, dc}, rng?)` 服务器端 D20 + checkDC | 纯（rng 可注入） |
| `failed-point-service.ts` | `isFailedPoint(list)` + `appendFailedPoint(sessionId, ep, step)` 事务幂等写 | 分离 |
| `prescreen-llm.ts` | `remix__prescreen` → `{ooc, attr?, dc?}` | I/O |
| `sync2-llm.ts` | `remix__sync2_patch` → `InsertPatch`，服务端回填 `source` / `remixId` / `createdAt` | I/O |
| `fail-narrative-llm.ts` | `remix__fail_narrative` → `{narrative}` ≤400 字符，有 static fallback | I/O |
| `forward-planner-llm.ts` | `remix__forward_planner` → `Record<episodeId, InsertPatch[]>`，强制 `insert_after only`，2-6 步 | I/O |
| `apply-patches.ts` | `applyPatches(episode, patches)` 纯函数。按 `createdAt` ASC 排序依次 splice；孤儿跳过 + warn | 纯 |
| `forward-plan-service.ts` | `enqueueForwardPlansFor` / `processForwardPlanJob` / `redispatchQueuedPlan` | I/O |
| `remix-service.ts` | 顶层 `submitRemix` / `commitRemix` / `processRemixSync2Job` orchestration | I/O |
| `main-backend-client.ts` | facade | 转发 |

## API 路由

所有路由走标准 envelope `{code, msg, data}`，HTTP 200 + 业务 code（只有 auth 用真 HTTP 401）：

| 路由 | 职责 |
|---|---|
| `POST /api/remix/submit` | 提交玩家输入，返回 prescreen 结果 + 预投骰 |
| `POST /api/remix/commit` | finalize remix；拿 patch 或 fail narrative |
| `POST /api/remix/drain-forward-plans` | 兜底：手动 redispatch 卡住的 forward plan 任务 |
| `GET /api/remix/session-patches` | `?sessionId&episodeId` → 累积 patches 列表 |
| `GET /api/remix/forward-plan-status` | `?remixId` → 3 个 plan 的状态 |

## LLM 调用管线

所有 LLM 调用走 `app/lib/langfuse-prompts.ts` + `app/upstream/llm-client.ts` 底座：

1. `getCompiledPrompt(id, variables)` 从 Langfuse 拉模板 + mustache 替换
2. `getLLMClient().chat({prompt, expectJson, temperature, maxTokens})` 调上游
3. Zod 校验。schema 违例 → `LLMUnavailableError`

| LLM | Prompt ID | 模式 | 档位 | 超时 | 重试 |
|---|---|---|---|---|---|
| Prescreen | `remix__prescreen` | 同步阻塞 | haiku 级 | 1.5s | 1 次 |
| Sync 2 | `remix__sync2_patch` | outbox 异步 | 中型 | 10s | 不重试 |
| Fail Narrative | `remix__fail_narrative` | 同步阻塞 | 轻量 | 5s | 不重试（有 static fallback） |
| Forward Planner | `remix__forward_planner` | outbox 异步 | 中型 | 60s | BullMQ 默认重试 |

**Prompt 公约**（dramatizer 风格 + remixer 的重述不变量技巧）：

```
# ROLE
# HARD RULES（重复 3 次）
# RUBRIC / ALLOWED
# INPUT（{{mustache}}）
# OUTPUT SCHEMA
# FEW-SHOT（generator 类有 1 个；judge 类没有）
# REMINDER（HARD RULES 再说一次）
```

特别加了 **system-word hygiene invariant**：系统词（butterfly / signal / affection / remix / patch / anchor / MSS / stepId）禁止出现在用户可见的 step text 里，防止提示词里 salient 词泄漏到故事文本。这条规则是 2026-04-25 上线后发现实际污染案例（LLM 把"butterfly"塞进 you.text 编出"'Butterfly' 短信"伪剧情）后补上的。

## BullMQ + Outbox 一致性

Remix 利用 main backend 已有的 outbox 基础设施：

```
submitRemix ── prisma tx ──► OutboxEvent(topic=remix.sync2,
                               status=pending,
                               dedupeKey=remix-sync2:<remixId>)
               dispatchOutboxNow ─► BullMQ ─► queue-worker
                                              │
                                     processRemixSync2Job
                                              │
                                     sync2-llm 调 → 写 Remix.patchJson
                                     OutboxEvent.status=completed

commitRemix (success) ── 类似路径 ──►
  3 个 RemixForwardPlan(status=queued) +
  3 个 OutboxEvent(topic=remix.forward_plan,
                   dedupeKey=remix-forward-plan:<planId>)
```

**关键保证**：
- outbox 事件和业务数据**同一事务**写入
- dedupeKey 保证 retry 幂等
- dispatcher 把事件推给 BullMQ：`dispatching → enqueued → processing → completed/failed`
- 卡住 5min 的 dispatching / 30min 的 enqueued + processing 会被自动 release 回 pending 重调度

## 数据库行为

### 涉及表

```
Session (已有，扩展 1 列)
├── failedRemixPoints  Json @default("[]")

Remix (新)                                  一次 remix 一行
├── id (uuid), sessionId, userId, novelId, episodeId
├── anchorStepId, targetType, targetId, inputText
├── ooc, oocReason, attr, dc
├── predeterminedRoll, predeterminedSuccess
├── status  submitted|ooc_blocked|rolling|
│           committed_success|committed_failed|
│           expired|generation_failed
├── gemsCharged, patchJson, failNarrative
├── index [sessionId, episodeId, anchorStepId]   failed_point + in-flight 查询
└── index [sessionId, status, createdAt]

RemixForwardPlan (新)                       每个 commit_success 创建 3 行
├── id, remixId, sessionId
├── batchRange Int[]  [startSeq, midSeq, endSeq]
├── status  queued|running|completed|failed
├── patchesJson  Record<episodeId, InsertPatch[]>
└── index [status, createdAt], index [remixId]

SessionPatch (新)                           玩家·集维度累积
├── id, sessionId, episodeId
├── patches Json  InsertPatch[]，createdAt ASC 排序
└── unique (sessionId, episodeId)  upsert key
```

### `Remix` 状态机

```
           submitted
              │
  ┌───────────┼───────────┐
  │           │           │
  │(ooc=true) │           │(prescreen failure ×2)
  ▼           ▼           ▼
ooc_blocked  rolling  ooc_blocked(oocReason=system_error)
              │
              │ sync2 via outbox
              ├── patchJson 写入 (仍 rolling)
              │
              ├── generation_failed (sync2 LLM 失败)
              │
              │ commitRemix called
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
committed_success   committed_failed
```

### 写入路径

**submit 路径**：
1. 开 prisma.$transaction
2. 查 failedRemixPoints、in-flight Remix
3. 创建 Remix(status=submitted)
4. commit
5. 调 prescreen LLM（≤1.5s）→ ooc 或 rolling
6. rolling 时服务器 `rollD20()` + `checkDC()`
7. 若 predeterminedSuccess=true → 开 tx 再次 + `enqueueOutbox('remix.sync2')`

**commit 成功路径**：
1. 短轮询 `Remix.patchJson` 最多 3s（100ms interval）
2. 外部 tx：`spendGemsForRemix(20)` —— ActionRecord marker + advisory lock 保幂等
3. 业务 tx：`upsert SessionPatch`（append-and-sort）+ `Remix.status=committed_success`
4. 非事务：`enqueueForwardPlansFor` —— 创建 3 个 plan + 3 个 outbox
5. 返回 `{success, patch, gemsCharged:20, forwardPlanJobIds}`

**commit 失败路径**：
1. 调 fail-narrative LLM（≤5s），失败 fallback to static string
2. tx：`appendFailedPoint` + `Remix.status=committed_failed`
3. 返回 `{success:false, failNarrative, gemsCharged:0, forwardPlanJobIds:[]}`

**forward plan 处理**（BullMQ worker）：
1. `listEpisodesInSeqRange(novelId, N+1, N+3)` 拿 batch 内 episodes（可能 <3 如小说不够长）
2. 调 forward-planner LLM（≤60s）→ `Record<episodeId, InsertPatch[]>`
3. 对每个 episodeId：`upsert SessionPatch`
4. `RemixForwardPlan.status=completed` + `patchesJson`
5. LLM 或 schema 失败 → status=failed + errorReason + rethrow（BullMQ 重试）

### 幂等性保证

| 机制 | 保证 |
|---|---|
| outbox `dedupeKey` | 同 key 重复 enqueue → 既有 pending 行被 update |
| BullMQ `jobId` = `encodeURIComponent(dedupeKey)` | 任务级去重 |
| poll-类 topic 附 `Date.now()-attempts` 后缀 | 允许多次 poll |
| gems spend | ActionRecord marker + advisory lock，一个 remixId 只扣一次 |
| `SessionPatch.patches` merge | 事务内 read-modify-write，sort deterministic |
| `failedRemixPoints` append | 事务内 has-check，同 (ep, step) 不重复 |
| Remix in-flight 查询 | 阻止同 anchor 重复 submit |

### 读取路径

玩家加载 session：
```
save-service.loadEpisodeFromSession(session)
  base = episode-service.loadEpisode(novelId, episodeId)
  patches = session-patch-service.loadSessionPatches(sessionId, episodeId)
  if patches.length == 0: return base
  patched = applyPatches(base.episode, patches)       ← createdAt ASC
  labelIndex = buildLabelIndex(patched)                ← 重建
  return { record, episode: patched, labelIndex }
```

`applyPatches` 的 anchor 解析是 cursor-path 级（不是 MSS step.id —— MSS 没有 id 字段）：
- `anchor.stepId = "5"` → 顶层第 5 步之后插入
- `anchor.stepId = "5.then.3"` → 解析首段 `5` 作为顶层索引（嵌套位置 `then.3` 被丢弃，spec §7 规定 splice 仅在顶层操作）
- 无效 anchor → 跳过 + `logEvent("warn", "remix.orphaned_patch")`

## 用户心流（前端 state machine）

```
idle
  ↓ （长按对白 / 点立绘）
typing         RemixInputBar 弹出，玩家输入 ≤50 字
  ↓ （Enter）
submitting     POST /api/remix/submit
  ↓
├─ ooc_blocked        显示 oocReason，点 dismiss → idle
├─ failed_point_blocked  toast "已锁定" → idle
├─ in_flight_conflict    toast → idle
└─ rolling             显示 DcCapsule（attr·DC·WIN%），点 Roll
     ↓
   dicing              RemixDiceModal 播 ~1.5s 动画
     ↓
   committing          POST /api/remix/commit
     ↓
   ├─ success          toast "Your remix landed!"
   │                   当前集 splice 3-8 步
   │                   3 个 forward plan 后台启动
   │                   扣 20 gems → idle
   └─ fail             显示 FailNarrativeOverlay 3s
                       failedRemixPoints 永久锁定
                       不扣 gems → idle
```

### 触发条件

| 触发 | 操作 | targetType |
|---|---|---|
| 长按对白 | 气泡上按住 ≥500ms | dialogue |
| 长按屏幕 | 背景任意位置按住 ≥500ms | dialogue |
| 点立绘 | 角色立绘单击 | character |
| 键盘 | Tab 到立绘 + Space/Enter | character |

**失败触发条件（静默 no-op）**：

- `currentLineCursorRef.current === null`（场景切换/phone modal 中）
- `interactionBlocked`（dice modal / minigame / decision / ending 开着）
- 短按 <500ms（算普通"继续"）

### DC 校准阶梯

Prompt 明确规定（`remix__prescreen.txt`）：

| DC | 难度 | 例子 |
|---|---|---|
| 5 | trivial | 角色会自然做的小事（好感度高时称赞衣服） |
| 10 | easy | 轻微社交代价（在酒吧请大家一轮） |
| 15 | challenging | 对方有理由拒绝（让怒气中的她笑出来） |
| 20 | hard | 强反对 + 公开失败风险（当面劝反派副手倒戈） |
| 25 | very hard | 会显著重塑场景（法庭上掏出能开脱的证据） |
| 30 | near-impossible | 临近 OOC 但世界观勉强允许（一己之力终结战争） |

如果动作会波及下一集（需要新场景消化），DC +5。

### 约束表

| 约束 | 实现 | 前端表现 |
|---|---|---|
| 同 (ep, step) 失败永久锁定 | `Session.failedRemixPoints` | toast "已锁定"，长按无反应 |
| 同 anchor 不能并发 submit | Remix status 查询 | toast "已有进行中" |
| 输入 ≤50 字 | 前后端双重校验 | InputBar 计数 + 禁用 |
| OOC 不扣 gems | commit 路径 | 不弹扣费动画 |
| DC 失败不扣 gems | commit 路径 | 不弹扣费动画 |
| 必须有 line 才能触发 | `currentLineCursorRef !== null` | 场景切换/phone 中无反应 |

### 状态可观测性

- `GET /api/remix/session-patches?sessionId&episodeId` —— debug 面板看累积 patches
- `GET /api/remix/forward-plan-status?remixId` —— 前端轮询"选择正在未来集发酵..."
- `POST /api/remix/drain-forward-plans` —— 兜底重拉（玩家态 or admin 态）

## Signal vs Butterfly 分工

Remix 写入的 session 状态有两类，spec §8 严格区分：

| 维度 | Signal | Butterfly |
|---|---|---|
| 作用域 | 集内（含未来集的内部分支） | 集外（长期倾向 / 跨集跳转） |
| 命名 | LLM 自由 snake_case | 自由文本描述 |
| 写入方 | Remix LLM + 编剧 `@signal` | 同上 + 编剧 `@butterfly` |
| 消费方 | Forward Planner + 未来集的 `@if` | [[concepts/signal-int-backend#influence]] 判定 |
| 能被覆盖 | 能（state） | 不能（trace） |

**关键原则**：state 用 signal，trace 用 butterfly。多次 remix 不抵消——玩家 remix #1 种了 violence butterfly、remix #2 种了 healing butterfly，两者共存。

## 与其他系统的关系

- [[concepts/mss-format]] —— Remix patch 里的 step 必须是 MSS step 白名单子集（排除 choice/gate/minigame/...）
- [[concepts/signal-int-backend]] —— Remix 生成的 `signal` / `@signal int` step 走既有 walker 写入，不双写
- [[concepts/novel-game-config]] —— Prescreen LLM 读 `attributeConfig.names` 判定 attr，DC 由玩家 attrValue 决定成功率
- [[entities/moonshort-backend]] —— 本系统整体实装在 moonshort-backend，BullMQ + Outbox 基础设施复用自该项目

## 和旧 Drama Remix 的关系

| 维度 | Drama Remix (M7) | Remix Anywhere (2026-04) |
|---|---|---|
| 触发 | session 结束/cursor | 长按对白 / 点立绘 |
| 范围 | 整集新 Episode | 当前集 InsertPatch |
| 延迟 | 数秒-数分钟（整集生成） | ≤1.5s prescreen + ~5s commit |
| 成本 | 全集 LLM | prescreen + sync2 + forward planner |
| 失败 | 重试重跑 | D20 机制 + 失败点锁定反滥用 |
| 持久化 | Episode 行 | SessionPatch / Remix / RemixForwardPlan |
| 未来 | bug-fix only | 活跃开发 |

两系统共存但互不干扰（outbox topic 命名空间分离：`drama-remix.*` / `assets-remix.*` vs `remix.sync2` / `remix.forward_plan`）。新功能全部走 Remix Anywhere；Drama Remix 冻结特性开发，仅修 bug。
