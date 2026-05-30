---
name: production-manifest-supabase-db
description: Supabase Postgres bootstrap + migration policy for moonshort-backend (PR #7 two-phase pipeline)
source_repo: cdotlock/moonshort-backend
source_files:
  - docs/operations/production-manifest-supabase-db.md
  - docs/architecture/migration-policy.md
fetched: 2026-05-30
status: source-of-truth-mirror
---

# Supabase Bootstrap + Migration Policy — Source Mirror (2026-05-30)

Mirror of upstream operations runbook and migration-policy doc. Wiki synthesis: [[concepts/supabase-backend-bootstrap]].

## Source files

- [`docs/operations/production-manifest-supabase-db.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/operations/production-manifest-supabase-db.md) — 2026-05-29，PR #7 two-phase pipeline 合入后改写
- [`docs/architecture/migration-policy.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/architecture/migration-policy.md) — 2026-04-27 决策 option A

## Quoted key invariants

> **Prisma migration 文件 = 增量 schema 补丁，假设上一次部署后的 prod DB 状态。本项目不支持从空库 replay 全部 migration。**

> 这是 2026-04-27 用户拍板的 option A（承认现状），不是 oversight。

> 灾备 **不依赖** migration replay 来恢复生产。

## Fresh Supabase bootstrap

Required env:

- `DIRECT_URL` — Supabase direct Postgres URL（端口 5432，**不**用 pooler）
- `BOOTSTRAP_TARGET_DB_NAME` — 预期 DB 名（防呆，脚本会先连进去 `SELECT current_database()` 比对）

```bash
export DIRECT_URL='postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres'
BOOTSTRAP_FRESH_SUPABASE_DB=yes \
BOOTSTRAP_TARGET_DB_NAME=postgres \
  pnpm db:bootstrap:fresh-supabase
```

Script固定顺序：

1. Supabase 平台扩展（`vector` / `pgmq` / `pg_cron` / `pg_net` / `supabase_vault`）
2. 合并 backend + dream Prisma schema
3. `prisma db push --accept-data-loss`
4. App contract SQL（CHECK、index、production manifest trigger）
5. pg_cron dream job sweeper
6. `pnpm db:assert-contracts`
7. `pnpm smoke:production-manifest-db`

## Accept criteria

```bash
DIRECT_URL="$DIRECT_URL" pnpm db:assert-contracts
DIRECT_URL="$DIRECT_URL" pnpm smoke:production-manifest-db
```

For full bootstrap details + linked variant + service-smoke flow, see source files.
