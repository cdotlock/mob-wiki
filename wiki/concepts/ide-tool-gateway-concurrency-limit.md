---
title: IDE Tool Gateway Concurrency Limits
tags: [backend, ide, concurrency, rate-limit, upstream, ops]
created: 2026-06-14
updated: 2026-06-14
---

[[entities/lunaverse-backend]] 的 IDE 工具网关（`/api/ide/tools/[toolId]`，所有用户的出图/视频/抠图等上游调用都过这道关）有**两层并发闸门**，保护上游提供商不被多用户聚合并发打爆。代码与上线状态见 PR [#15](https://github.com/cdotlock/lunaverse-backend/pull/15)（分支 `feat/ide-concurrency-limiter`，3 个 commit）。

## One sentence

每个非 admin 用户**最多 2 个在途上游调用**（per-user cap），且每个上游端点有一个**自学习的全局并发上限**（per-pool cap）——上游回 429/503/超时就自动减半、健康时回升到保守默认值、绝不越过默认值（除非显式开探测），floored 还在过载就熔断；两层都满就服务端排队、等不到才回 429。**admin 免 per-user cap 但仍受全局 cap + 熔断约束**。

## 为什么这样做（决策记录）

- **必须放后端网关**：只有共享网关看得到「所有用户加起来」的并发；每个用户的 IDE 客户端只看得到自己，无法跨用户保护上游。
- **per-user cap（第 1 层）**：防单用户独占。满了**服务端等待**（默认 45s）再回 `429 at_capacity`——因为 assetctl 客户端对 429 重试很差（[gpt.go] 只重试 2 次、零退避、不读 `Retry-After`），所以队列放服务端、不靠客户端重试。
- **per-pool 全局 cap（第 2 层）**：per-user 挡不住 N 用户 × 2 超过上游总量（如第 6 个用户把总在途顶过 ~10）。每个在途租约打上 `poolId`（上游 URL env-var 名，**共享同一端点的工具共用一个上限**），acquire 再查一道「该 pool 在途 < 该 pool 的自适应上限」。
- **存储用 Postgres 不用 Redis**：**生产没有 Redis**（已被 pgmq 取代，见 [[concepts/backend-security-hardening-2026-06]] / `app/lib/rate-limit.ts` 注释）。多实例（Railway 多无状态容器）唯一共享态就是 DB。这是 workflow 初版设计假设 Redis 的纠正。
- **自适应而非静态（关键）**：上游真实并发上限未知且各家不同、无法向 API 查询。所以全局上限**从观测信号自学习**——只**向下**夹紧（OVERLOAD 减半），健康时**回升到保守 staticDefault 但不越过**。安全属性：**自适应只在已知安全值以下夹，永远不会把自己调成事故**（要发现「上游其实能扛更多」唯一办法是真把它压垮，故默认不向上探测，留 `IDE_POOL_PROBE_ABOVE_DEFAULT` 开关）。这条排除了 AIMD（慢且会向上赌）和延迟梯度（出图 RTT 由任务大小主导、信号噪声大）两个候选。
- **admin 仍受全局 cap（对抗式审查抓到的修复，commit `e91da6c9`）**：初版让 admin 完全跳过 acquire，结果 admin 调用不计入全局 cap、也绕过熔断——而这正是最初的隐患场景（admin 用 IDE agent 跑大批量出图把上游打爆）。修正：admin **仍 acquire、仍占 pool 槽、仍受熔断**，只是把 per-user cap 抬成 `Infinity`。全局 cap 是上游的物理极限，不在乎谁在调。

## 数据模型

- **`IdeConcurrencyLease`**：一行 = 一个在途上游调用。`leaseId`(PK) + `userId` + `poolId`(默认 `''`) + `expiresAt`。per-user 计数按 `userId`、全局计数按 `poolId`，release 按 `leaseId` PK。无二级索引（表只存在途租约，量极小，seq-scan 即可）。`expiresAt` 让崩溃/超时请求的槽自愈。
- **`IdeConcurrencyPool`**：一行 = 一个上游端点的自适应状态。`poolId`(PK) + `limit`(当前学到的上限) + `staticDefault`(默认不越过) + `minLimit`(地板，≥1) + `successCount` + `lastDecreaseAt`(冷却锚) + `circuitState`(`closed`/`open`) + `circuitOpenAt` + `updatedAt`。注意 `limit` 是 SQL 保留字，所有原始 SQL 必须双引号 `"limit"`。
- 迁移 `20260613000000_ide_concurrency_lease`（建租约表）+ `20260614000000_ide_concurrency_pool`（`ALTER ADD COLUMN poolId` + 建 pool 表），都是在线安全的 ADD COLUMN/CREATE TABLE。

## Acquire（关键不变量）

`acquireConcurrencySlot(userId, poolId, cfg)` 在**一个事务里持两把 transaction-scoped advisory 锁**（per-pool + per-user，**固定排序加锁**，杜绝死锁）做：① 查/初始化 pool 行 + 检查熔断 ② 删过期租约 + per-user 计数（≥cap → full）③ per-pool 计数（≥limit → full）④ 插入租约。per-pool 锁把「该 pool 的计数→插入」跨实例串行化，杜绝超发；锁只持有这几毫秒事务、**不跨那个慢的上游调用**（租约行守护它）。**DB 出错 fail-open**（返回 null 租约、放行）——限流器挂了绝不拖垮网关。`full` 走 wait-then-429，`circuitOpen` 快速回 `503 pool_unavailable`。

## 自适应控制环 `recordPoolSignal`

网关 route 在 `finally` 里 fire-and-forget 喂一个信号（不阻塞请求）：

- **信号分类**：上游 `HTTP 429/503/529` 或 `timeout/ECONNREFUSED/ECONNRESET/socket hang up` → **OVERLOAD**；其余（含 2xx 成功、以及 400/401/500 这类非容量错）→ **HEALTHY**（不为客户端/上游普通故障误降速）。
- **OVERLOAD**：冷却窗内（默认 30s）则忽略（防抖）；否则 `limit = max(minLimit, floor(limit × 0.5))`、记 `lastDecreaseAt`；已在地板还过载 → 开熔断（`circuitState='open'`，快速 503，过 `BREAKER_TIMEOUT` 后半开放一个探测）。
- **HEALTHY**：累计成功，满 `successTarget`（默认 10）个后 `limit += 1`，封顶 `staticDefault`（开了探测才到 `poolMaxLimit`）。
- 所有调整都在 per-pool advisory 锁内、单独小事务——多实例不会撕裂 read-modify-write，也不会对同一波 429 重复减半（第二个实例在锁内看到 `lastDecreaseAt` 命中冷却而 no-op）。每次状态转移都打结构化日志（`pool_decreased`/`pool_increased`/`pool_overload_cooldown`）。
- **可观测**：当前学到的上限直接可查 `SELECT "poolId","limit","staticDefault","circuitState","lastDecreaseAt" FROM "IdeConcurrencyPool"`；`limit < staticDefault` = 该 pool 正被夹，`circuitState='open'` = 上游疑似挂了。

## Env 开关（改了不用改代码重新发版）

| 变量 | 默认 | 含义 |
|---|---|---|
| `IDE_BETA_CONCURRENCY` | 2 | per-user 在途上限 |
| `IDE_CONCURRENCY_WAIT_MS` | 45000 | 抢不到槽时最多等多久再回 429 |
| `IDE_CONCURRENCY_LEASE_MS` | 360000 | 租约 TTL（须 > 最长上游调用 ~300s，防误回收）|
| `IDE_POOL_STATIC_DEFAULT` | 8 | pool 全局上限的封顶默认值（+ 每 pool 可覆盖 `IDE_POOL_<SLUG>_STATIC_DEFAULT`）|
| `IDE_POOL_MIN_LIMIT` | 1 | pool 地板（永不全关）|
| `IDE_POOL_DECREASE_FACTOR` | 0.5 | OVERLOAD 时乘的因子 |
| `IDE_POOL_INCREASE_STEP` | 1 | HEALTHY 回升步长 |
| `IDE_POOL_SUCCESS_TARGET` | 10 | 升一格需多少连续健康调用 |
| `IDE_POOL_COOLDOWN_MS` | 30000 | 两次减半之间的最小间隔（防抖）|
| `IDE_POOL_BREAKER_TIMEOUT_MS` | 120000 | 熔断打开后多久半开 |
| `IDE_POOL_PROBE_ABOVE_DEFAULT` | false | 是否允许向上探测越过 staticDefault（默认关）|

> **部署注意**：应用两个迁移；按各上游真实能力设每个 pool 的 `staticDefault`（视频类设低，如 3–4；图像类可高）；默认值对未知上游是安全的保守起点。

## 验证（2026-06-14）

单元 + 路由测试 **101 全过**、`tsc` 干净、迁移安全 lint 0 错；**真 Postgres 实测**（`scripts/ide-concurrency-smoke-test.ts`，证 advisory-lock 原子性，mock 测不出）全场景过：per-user 6 并发只放 2、**跨 3 个不同用户全局上限 3 只放 3**、**admin 批量 5 个被 pool 上限 2 夹住**、OVERLOAD 把上限 4→2、健康 4→5 且封顶 8、熔断开/快速 503/半开/恢复。对抗式审查（4 视角找 bug + 逐条反驳）confirm 1 真 bug（admin 绕过全局 cap，已修），驳回 2 个时钟偏移误报。

## Related

- [[entities/lunaverse-backend]] — 承载网关的服务
- [[concepts/backend-security-hardening-2026-06]] — 同仓的 Postgres 限流地基（auth 的**速率**窗口限流；本页是**并发**在途限流，不同语义、复用同套 fail-open + 无 Redis 哲学）
- [[entities/mob-ai-router]] / [[concepts/cli-gateway-protocol]] — 被保护的上游与网关协议背景
- [[entities/lunaverse-ide]] — 发起这些上游调用的客户端（assetctl 经 IDE gateway 远程模式）

## Canonical source

- 代码：`app/lib/ide-concurrency.ts`（两层 acquire + `recordPoolSignal` 自适应环）、`app/upstream/ide-tool-gateway.ts` → `poolIdForTool`、`app/api/ide/tools/[toolId]/route.ts`（接线）
- schema：`prisma/schema.prisma` → `model IdeConcurrencyLease` / `model IdeConcurrencyPool`；迁移 `prisma/migrations/20260613000000_ide_concurrency_lease/`、`20260614000000_ide_concurrency_pool/`
- 测试：`app/lib/ide-concurrency.test.ts`、`app/lib/ide-concurrency-pool.test.ts`、`__tests__/api/ide/tools-route.test.ts`、`scripts/ide-concurrency-smoke-test.ts`
- PR [#15](https://github.com/cdotlock/lunaverse-backend/pull/15)
