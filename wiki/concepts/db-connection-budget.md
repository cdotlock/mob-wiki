---
title: DB 连接预算：Supavisor transaction 池 + 每引擎显式 cap
tags: [backend, supabase, postgres, supavisor, pooling, ops, incident]
sources: [raw/2026-06-10-db-connection-exhaustion-fix.md]
created: 2026-06-10
updated: 2026-06-10
---

2026-06-10 [[entities/lunaverse-backend]] 连接耗尽修复（branch `fix/db-connection-exhaustion`，源 doc：[`docs/operations/2026-06-10-db-connection-exhaustion-fix.md`](https://github.com/cdotlock/lunaverse-backend/blob/fix/db-connection-exhaustion/docs/operations/2026-06-10-db-connection-exhaustion-fix.md)）。背景：2026-05-30 `EMAXCONNSESSION` 炸过生产 deploy（见 [[concepts/railway-production-deploy]]）；上线前必须解决高并发连接耗尽。

## 一句话

**运行时一律走 Supavisor transaction 池（6543，自动 `pgbouncer=true`），每个 DB 引擎在代码里给显式 `connection_limit`；session 池（5432）只给 CI migrate，direct host 只给 operator DDL。**

## 为什么会耗尽（生产实测，2026-06-10）

- Supabase Micro：`max_connections=60`，系统自身吃 ~10-12 条。
- Supavisor session 池**不复用**：1 client = 1 server conn，per (user×db) 上限 = `default_pool_size` = **15**。probe 实测：18 并发 → 15 成功，第 16 条起 `EMAXCONNSESSION`。
- 消费者全是裸客户端：app/worker **各 2 个** Prisma 引擎（main + dream），默认池 = 宿主核数×2+1（容器读宿主核数，17~33 条/引擎且随机器浮动）；tts 第 3 个引擎；dream-rec SQLAlchemy 池 20+40=60/进程 × 2 进程（api + outbox worker）。任何组合都能瞬间打满 15。

## 修了什么

- URL 归一化进代码（`app/lib/db-url.ts` + dream/tts 副本 + drift test）：6543 自动补 `pgbouncer=true`；缺 `connection_limit` 按角色补默认（app 主 10 / worker 主 6 / dream 5·4 / tts 4，env 可覆盖）；指回 session 池启动告警。env 纪律不再是承重墙。
- dream-rec：池 5+5/进程；6543 时 asyncpg `statement_cache_size=0` + 唯一 prepared statement 名；alembic 走 `MIGRATION_DATABASE_URL`。
- CI migrate：`scripts/derive-session-url.cjs`（`MIGRATION_SESSION_URL` 优先，否则 6543→5432 去参）——runtime 切 6543 后 prisma migrate 不能再裸用 `DATABASE_URL`。
- `/api/health` 新增 `dbConnections` gauge；`scripts/db-pool-probe.ts` 可复跑全部证据。

## 关键验证

- transaction 池 6543 实测：**50 并发 client 复用 17 条 server conn**，全部成功。
- Prisma 功能面过 6543 全通：`$transaction` + `pg_advisory_xact_lock`（save-service 三处串行化锁的精确形态——xact 级锁在事务内 pin 单 server conn，transaction 池安全）+ 20 并发查询在 connection_limit=5 下排队不报 P2024。
- 代码无 session 级特性（无 `pg_advisory_lock`、LISTEN/NOTIFY、session GUC、temp table），切换无兼容性负担。

## 切换注意（merge 后 ops 执行）

Railway 各 service `DATABASE_URL` 改 6543；app 加 `MIGRATION_SESSION_URL`；dream-rec 加 `MIGRATION_DATABASE_URL`；`DIRECT_URL` 不动。验收：启动日志 `[db] pool ...:6543 ... pgbouncer=true`、health `dbConnections` ≤ 15、probe 复测。详见源 doc §3。

## 相关

- [[concepts/railway-production-deploy]] — deploy workflow / 2026-05-30 事故上下文
- [[concepts/supabase-backend-bootstrap]] — DB bootstrap / migration 政策（direct host 用途）
- [[entities/lunaverse-backend]]
