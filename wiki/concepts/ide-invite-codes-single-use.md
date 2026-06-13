---
title: IDE Single-Use Invite Codes
tags: [backend, ide, invite, auth, ops]
created: 2026-06-12
updated: 2026-06-12
---

[[entities/lunaverse-backend]] 的 IDE beta 邀请注册用 **DB 里的单次使用邀请码**。本页是设计决策 + 数据模型 + 运维知识；逐条可照抄的命令在仓库 `docs/ide-invite-codes-runbook.md`（canonical），env 类配置见 [[concepts/railway-production-deploy]] 的姊妹文档 `docs/ide-backend-env-runbook.md`。

## One sentence

注册接口 `/api/ide/register` 在一个事务里从 `IdeInviteCode` 表**原子认领**一个未用码（`updateMany(where usedByUserId IS NULL)`），**一码一用、并发安全**；授权档位（role/plan/quota）存在每条码上，默认 beta。

## 为什么这样做（决策记录）

- 初版（IDE invite registration，PR [#11](https://github.com/cdotlock/lunaverse-backend/pull/11)）用单个 env 变量 `IDE_INVITE_CODE`：全局一个码、可无限复用、不记消耗。
- 产品需求改为「发 100 个码、任意一个都能注册、但**一码一用**、额度默认」。单次使用必须把「已消耗」持久化到 DB —— env 做不到。
- 落地：新增 `IdeInviteCode` 模型 + 迁移 `20260612000000_ide_invite_codes`，注册路由从「env 比对」改为「事务内 DB 认领」，删掉 env 单码路径与 `resolveIdeInviteCode`（`normalizeCode` 保留为共享规范化 util）。
- 提交：`ffd4327f`（feature）、`0997a627`（env/runbook 同步、删掉作废的 `IDE_INVITE_*`）、`4265a51b`（dedicated runbook）。

## 数据模型 `IdeInviteCode`

`code`（唯一，存大写规范化后的码）+ `role`/`plan`/`monthlyTokenQuota`/`monthlyStorageQuotaMb`（默认 `beta_user` / `beta` / 2 000 000 / 2048）+ `usedByUserId?` / `usedAt?` + `createdAt`。**未用 = `usedByUserId IS NULL`**。授权字段在注册时被拷到新建 `User` 上（`ideStatus=active` 等）。

## 并发安全（关键不变量）

注册事务：① 查码（不存在/已用 → 拒 2003）② 查用户名（占用 → 拒 2002，**不消耗码**）③ 建 `User` ④ `updateMany(where id, usedByUserId IS NULL)` 认领 —— `count !== 1` 抛错、**整笔回滚**。两个请求抢同一个码，第二个 `count=0`，不会建出账号。大小写不敏感（输入 `trim+uppercase` 后比对）。

## 运维摘要

- **生成**（离线、码不入 git/wiki）：`/dev/urandom` + 去混淆字母表，格式 `LUNA-XXXX-YYYY`。当前 100 个码在运维机 `~/lunaverse-ide-invite-codes.md`。
- **灌库**：psql over `DIRECT_URL`，`INSERT ("id","code") VALUES (gen_random_uuid()::text,'…') ON CONFLICT ("code") DO NOTHING`（幂等，其余列走默认）。
- **发放**：一人一码，IDE「Create with invite」填 username/password/inviteCode。
- **监控**：`count FILTER (WHERE "usedByUserId" IS NULL)` 看余量；join `User` 看谁用了哪个码。
- **作废**：删未用码 `DELETE … WHERE code=… AND "usedByUserId" IS NULL`；停用**已注册**用户用 `User.ideStatus='suspended'`（改码不影响已注册账号）。

## 迁移怎么上生产

生产部署默认 `skip_migrations=true`（原因见 [[concepts/railway-production-deploy]]）。本迁移走操作侧：用 `DIRECT_URL` 跑 `migration.sql` 建表，并在 `_prisma_migrations` 补一行（`gen_random_uuid()` id + 迁移文件的 sha256 checksum + `finished_at=now`），再 `skip_migrations=true` 部署。

> **过期标记（2026-06-12 实测）**：生产库现在**有** `_prisma_migrations` 表并已记录 `2026060…`–`20260611000000_ide_auth_usage` 等迁移（其中 `20260610000200_session_hot_update_restore` 有一条 `finished_at IS NULL` 的历史 UNFINISHED 重复行）。这与 [[concepts/railway-production-deploy]] 里「prod 无 `_prisma_migrations`、纯 `db push` 管理 → in-CI 必 P3005」的旧描述**不再一致**；现在 in-CI migrate 被跳过的有效原因是 IPv6/pooler 15-client 上限 + 那条 UNFINISHED 行（会触发 P3009），而非 P3005。该页待更新。

## 排障速查

| 业务码 | 含义 |
|---|---|
| 2003 | 码不存在或已用（注册「Create with invite」失败最常见原因） |
| 2002 | 用户名占用（此时**不**消耗码） |
| 1001 | username 3-20 / password 6-50 校验不过 |
| 1429 (HTTP 429) | 注册按 IP 限流 5 次/小时 |
| 500 + `IdeInviteCode` 不存在 | 迁移没在生产库执行（见上「迁移怎么上生产」） |

## 验证（2026-06-12 上线时）

单测 7/7（认领消耗 / 未知码 / 已用码 / 用户名占用不消耗 / 并发竞态）、`tsc` 干净、迁移安全 lint 0 错；生产真机 e2e：有效码 → `code 0`+token、同码再注册 → `2003`、无效码 → `2003`，验证后删测试用户 + 复位码，线上回到 100/100 全可用。

## Related

- [[entities/lunaverse-backend]] — 承载注册接口的服务
- [[concepts/railway-production-deploy]] — 部署 workflow / skip_migrations / 账号 token 鉴权（本页迁移流程的上下文；其 `_prisma_migrations` 描述已过期，见上）
- [[entities/lunaverse-ide]] — 邀请注册的客户端入口（Create with invite）
- [[concepts/backend-security-hardening-2026-06]] — 码是访问凭证；secret 只留 backend 的安全前提

## Canonical source

- 仓库 `docs/ide-invite-codes-runbook.md`（逐条命令）、`docs/ide-backend-env-runbook.md`（env）
- 代码：`app/api/ide/register/route.ts`、`app/lib/ide-invite.ts`、`prisma/schema.prisma` → `model IdeInviteCode`、`prisma/migrations/20260612000000_ide_invite_codes/`
