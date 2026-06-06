---
title: Supabase Postgres Bootstrap + Migration Strategy
tags: [backend, supabase, postgres, migration, ops]
sources: [raw/2026-05-30-production-manifest-supabase-db.md, raw/2026-05-30-migration-policy.md]
created: 2026-05-30
updated: 2026-05-30
---

2026-05-29 [[entities/moonshort-backend]] 把生产 Postgres 切到 **Supabase**（Railway app/worker/tts/dream 服务全部指向同一个 hosted Postgres）。本页记录：（1）新建 Supabase 空库的 fresh-bootstrap 流程（必须，不能走 `prisma migrate deploy`），（2）项目历史 migration 的 **"增量补丁、不可 replay"** 既定决策与灾备方案。源 doc：[`docs/operations/production-manifest-supabase-db.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/operations/production-manifest-supabase-db.md) + [`docs/architecture/migration-policy.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/architecture/migration-policy.md)。

## 一句话

**Prisma migration 文件 = 增量 schema 补丁，假设上一次部署后的 prod DB 状态。本项目不支持从空库 replay 全部 migration。** 这是 2026-04-27 用户拍板的 option A（承认现状），不是 oversight。Supabase 新库走专用 `db push + raw contract SQL` bootstrap。

## 为什么不能 fresh-replay

1. **M1 (`20260420120000_m1_teardown_and_achievement_normalize`)** 通过 `DELETE FROM "SaveLog"` / `DROP TABLE` 拆**老**架构表（`SaveLog`、`Type1Config`、`Type2Config`、`Type3Config`、`AchievementType` 枚举等）。这些表 / 枚举不是由更早的 migration 创建的 —— 它们是 v3 时代用 `db push` 直接落库的产物，没有 baseline migration。
2. 因此空库执行 `migrate deploy` 时 M1 会在 `DROP` / `DELETE` 一个不存在的表 / 列时失败。**不是 bug，是历史**：v4 重构时选择了 db push 演化而非补 baseline。
3. 给 v4 补 baseline = 重写历史 = 跟生产已部署的 migration 表 checksum 冲突 = 现网每个环境都要手动 reset migration 表。**风险 > 收益**，所以维持现状。

## Dev / Prod / 新环境三分流

| 场景 | 命令 | 行为 |
|---|---|---|
| **本地开发** | `pnpm db:push` | 直接把 `schema.prisma` 同步到 DB，**不**走 migration；schema drift 直接覆盖 |
| **生产部署** | `pnpm prisma migrate deploy` | 按 `prisma/migrations/` 顺序应用尚未部署的 migration |
| **新环境**（Supabase 空库 / staging） | `pnpm db:bootstrap:fresh-supabase` | 见下 |

## Fresh Supabase Bootstrap

### 必填 env

- **`DIRECT_URL`** — Supabase direct Postgres URL（端口 5432，**不**用 pooler）
- **`BOOTSTRAP_TARGET_DB_NAME`** — 预期的目标 DB 名（通常 `postgres`）。脚本先连进去 `SELECT current_database()`，跟这个变量不匹配直接 abort。**防呆**：避免把 staging URL 配进 prod env 后误炸真库
- 可选 `DATABASE_URL`：runtime pooled URL；bootstrap 用 `DIRECT_URL` 做 DDL

### 走法

```bash
cd /path/to/moonshort-backend
export DIRECT_URL='postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres'

BOOTSTRAP_FRESH_SUPABASE_DB=yes \
BOOTSTRAP_TARGET_DB_NAME=postgres \
  pnpm db:bootstrap:fresh-supabase
```

`BOOTSTRAP_FRESH_SUPABASE_DB=yes` 是故意的保险 —— 这个命令只给空库或一次性 staging 用，不要随手打到现有生产库。

### 脚本固定顺序

1. 跑 Supabase 平台扩展：`vector`、`pgmq`、`pg_cron`、`pg_net`、`supabase_vault`
2. 合并 backend + dream Prisma schema
3. `prisma db push --accept-data-loss`
4. 跑 app contract SQL：CHECK、index、production manifest trigger
5. 跑 pg_cron dream job sweeper
6. `pnpm db:assert-contracts`
7. `pnpm smoke:production-manifest-db`

### 本地 ad-hoc 变体

本地临时 Postgres 没有 Supabase 托管扩展时，只验 app schema + production manifest contract：

```bash
export DIRECT_URL='postgresql://postgres:postgres@127.0.0.1:5432/moonshort_test'
BOOTSTRAP_FRESH_SUPABASE_DB=yes \
BOOTSTRAP_TARGET_DB_NAME=moonshort_test \
BOOTSTRAP_APPLY_PLATFORM_SQL=false \
BOOTSTRAP_APPLY_CRON_SQL=false \
pnpm db:bootstrap:fresh-supabase
```

### linked 变体（无法直连 Postgres，但 Supabase CLI 可用）

```bash
supabase link --project-ref <project-ref> --password '<db-password>' --skip-pooler
BOOTSTRAP_FRESH_SUPABASE_DB=yes \
BOOTSTRAP_TARGET_DB_NAME=postgres \
BOOTSTRAP_EXPECTED_PROJECT_REF='<project-ref>' \
pnpm db:bootstrap:fresh-supabase-linked
```

走 Prisma 生成空库 → 当前 schema 的 SQL，再通过 Supabase Management API 执行。仍然只适合全新空库。

### 验收硬指标

```bash
DIRECT_URL="$DIRECT_URL" DATABASE_URL="$DIRECT_URL" pnpm db:assert-contracts
DIRECT_URL="$DIRECT_URL" DATABASE_URL="$DIRECT_URL" pnpm smoke:production-manifest-db
```

- 第一条查结构：关键索引、CHECK、函数、触发器、字段非空、默认值
- 第二条查行为：插入两本测试小说和两份 release，确认同一 OSS 文件可复用 + 跨小说资产/语音/episode 引用被 DB 拒绝；脚本在事务里 rollback，不留测试数据

验证两阶段 service 全流程（submit → activate → rollback → reject）会真实写 release snapshot 时，用 runtime URL：

```bash
ALLOW_PRODUCTION_RELEASE_SERVICE_SMOKE=yes \
DATABASE_URL="$DATABASE_URL" DIRECT_URL="$DATABASE_URL" \
pnpm smoke:production-release-service
```

这条会留下一本 `Assets Dev Smoke ...` 测试小说做人工检查（含被 supersede 的旧 release 行）。

## 灾备 = DB 备份 / restore，不是 migration replay

**不依赖** migration replay 来恢复生产。新环境 / 灾备恢复的标准流程：

1. **DB 备份**：`pg_dump -Fc` + `pg_restore`。生产部署前先做 snapshot（runbook §1）；灾备直接 restore
2. **schema 漂移检测**：定期 `prisma migrate status` 在生产 DB 运行；发现 drift 走人工核对，**不**自动 reset
3. **新环境（完全空库的 staging / Supabase project）**：跑 fresh bootstrap（上节）；之后如需让 `prisma migrate deploy` 接管，再人工把历史 migration 标记为已应用（`prisma migrate resolve --applied <name>`）

## 维护规则

- 新增任何 "Prisma 表达不了但运行时必须保证" 的 DB 规则，放进 `supabase/migrations/*`，并同步加进 `scripts/assert-db-contracts.ts`。voice profile partial unique index `idx_character_voice_profile_active` 是当前最关键的一条 —— drop 掉就会让同一角色同时挂多份 active 语音
- 新增 production manifest 跨表规则时，同时扩展 `pnpm smoke:production-manifest-db`
- IDE manifest 字段新增：backend 先扩 schema/service/test，再让 IDE 发新字段
- L1 字段（玩家可见）必须由 activate 推 —— **严禁让 submit 直接动 L1**
- 多小说是默认场景。任何 asset、voice、prompt、episode 关系都必须能追溯到 `novelId` 和 `releaseId`
- `Novel.activeReleaseId` 是 "what's live" 的唯一真相。任何绕过 service 的 raw SQL 写入都必须配套跑 `pnpm tsx scripts/sync-active-release.ts <novelId>` 把 L1 推平

## 如果将来要做"完整可重放"

需要：

1. 重写 M1 之前所有 "被 db push 落库" 的状态为 baseline migration（`prisma migrate dev --create-only --name baseline`）
2. 跟生产 DB 协调 checksum reset
3. 把本地校验流程换成 fresh-Postgres + migrate deploy

是单独的大票，不在 cleanup-2026-04-27 plan 范围内。决策锚在 [`docs/architecture/migration-policy.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/architecture/migration-policy.md)。

## 决策史

- **2026-04-24** — staff-oncall 审计（P1-DEPLOY-002）把 "migration 不能从空库 replay" 列为 P1
- **2026-04-27** — 用户决策选 option A（承认现状）。理由：生产已运行；现有 db push + 手写 contract migration 在本地 E2E 都验证过；重构 baseline 风险大于收益
- **2026-05-29** — Supabase 切换完成，PR #7 two-phase pipeline 合入；本 doc 写出来作为 Supabase fresh-bootstrap 唯一权威 runbook

## 相关

- [[concepts/railway-production-deploy]] — 运行时部署面（CI workflow / 鉴权 / additive-only 零删库 cutover）；本页是其 DB / migration 政策依据
- [[concepts/production-pipeline-two-phase]] — 写库的两阶段流程，依赖本页的 DB 结构 invariant
- [[entities/moonshort-backend]] — 服务载体；Railway 上 5 个 service 全指向同一个 Supabase
