---
title: dream-rec monorepo migration (2026-05-24)
updated: 2026-05-24
tags: [dream-rec, monorepo, deployment, migration, moonshort-backend]
status: pr-open-railway-pending
---

# dream-rec monorepo migration

把 `AugustZAD/dream-rec` 整体搬进 `cdotlock/moonshort-backend` 仓的 `services/dream-rec/`，使用 `git subtree add` 保留完整历史。代码层面 monorepo，运行时仍然独立 container + HTTP 通信。

## Decision

- **Motivation:** 部署简化 ("demo 阶段先合，后面统一拆")。同事接管部署 ("我直接部署就行了")。
- **Approach:** monorepo + 独立 service（不是 supervisord 多进程）；学 `services/dream-agent/` 的容器化模式；运行时仍走 HTTP 通信。
- **Scope chosen:** 只落代码 + Dockerfile + 本地 dev 入口 + env 文档说明；**不**改 Railway workflow（同事在 Railway dashboard 手动建第 5 个 service）。

## Result (2026-05-24)

| 工件 | 位置 | 内容 |
|---|---|---|
| Subtree merge | `d816a19e` | `git subtree add --prefix=services/dream-rec ~/MobAI/dream-rec main` — 100+ 上游 commit 作为 ancestor history |
| Dockerfile | `c219e44f` | Python 3.12-slim + uv，多层 cache，non-root `appuser`，`/health` healthcheck，port 8766 |
| docker-entrypoint.sh | `c219e44f`（同 commit） | `alembic upgrade head` 幂等执行 → `exec` uvicorn |
| Dev compose | `0d92ac1b` | `docker-compose.dev.yml` 加 `dream-rec` + `dream-rec-worker` 两 service，`--profile dream-rec` opt-in |
| Prod env keys | `8b5d95bd` | `.env.production.example` 加 dream-rec 段：backend 侧 `DREAM_REC_URL/BEARER/ENABLED` + dream-rec 侧 `DATABASE_URL`（asyncpg）/`MOB_AI_*`/`BACKEND_INTERNAL_*` |
| README handover | `fdbb178f` | `services/dream-rec/README.md` 加 ops 在 Railway dashboard 建 service 的逐步操作指南 |

**Branch:** `feat/dream-rec-monorepo` pushed to `cdotlock/moonshort-backend` → **PR [#4](https://github.com/cdotlock/moonshort-backend/pull/4) opened 2026-05-24，等同事 review。**

**验证:**
- `uv run pytest -q` → 367 passed in 61s（跟 standalone 仓 baseline 一致）
- `uv run ruff check app tests scripts` → clean
- `docker build -t dream-rec:test services/dream-rec` → success，1.31GB，`appuser` runtime

## Why subtree (and not submodule)

用户选 `git subtree add` 不带 `--squash`，理由：完整保留 dream-rec 100+ commit history，相当于在 `services/dream-rec/` 路径下能追溯每个 component 的 commit。代价是 PR 的 commit 列表长（141 个 commits ahead of main），但 GitHub diff 视图干净（只看 `services/dream-rec/`）。Submodule 被排除是因为 monorepo 部署初衷之一就是消除"两个仓两套 build"的 ops 摩擦。

## Production-deploy gate (handover)

dream-rec 在 Railway 部署需要 ops 在 dashboard 手动操作：

1. New Service → Empty → name = `dream-rec`
2. Root dir = `services/dream-rec`，Dockerfile 自动检测
3. Env vars 按 `.env.production.example` § dream-rec 配齐
4. Private networking 打开，hostname → `dream-rec.railway.internal:8766`
5. 同时把 `app` + `worker` service 的 `DREAM_REC_URL=http://dream-rec.railway.internal:8766` / `DREAM_REC_BEARER=<same>` / `DREAM_REC_ENABLED=true` 配上（顺序：dream-rec 起来 healthy 后再翻 backend 端的 ENABLED）
6. `.github/workflows/railway-production-deploy.yml` 加 `railway up --service dream-rec --ci ...`（**单独 PR**，避免 Railway service 还没建好就把 CI 撞红）

完成前 `DREAM_REC_ENABLED=false` 保持 backend 端 hook no-op，零外向流量，安全。

## Archive

- `AugustZAD/dream-rec` 仓打了 annotated tag `pre-monorepo-2026-05-24`（HEAD `03c2d32`，README 顶部加 archived 横幅），未来不动。链接：[`pre-monorepo-2026-05-24`](https://github.com/AugustZAD/dream-rec/releases/tag/pre-monorepo-2026-05-24)
- patches 存档：`services/dream-rec/docs/integration-patches/000{1,2,3}-*.patch` + README（offline 同事 hand-off 备份）
- 设计文档双地址：原仓 + monorepo（因为 subtree merge 把 docs 一起搬了）

## Why "code-landed, Railway-pending" 而不是"shipped"

代码在 cdotlock 远端分支了 + PR 开了，但生产链路尚未跑通：
- ❌ Railway service `dream-rec` 还没建（ops 工作）
- ❌ `app` / `worker` 的 `DREAM_REC_ENABLED` 还是 false（设计如此，gate 在 ops 那一步）
- 🟡 [PR #4](https://github.com/cdotlock/moonshort-backend/pull/4) 等同事 review + merge
- ✅ 但 backend [[concepts/dream-rec-integration-architecture#moonshort-backend-integration-pr-3-merged-2026-05-24|PR #3]] 三个 hook commit 早已合到 backend `main`，等环境变量翻 true 就生效

## References

- **Spec:** `services/dream-rec/docs/superpowers/specs/2026-05-24-dream-rec-monorepo-migration-design.md`
- **Plan:** `services/dream-rec/docs/superpowers/plans/2026-05-24-dream-rec-monorepo-migration.md`
- **C0 integration architecture:** [[concepts/dream-rec-integration-architecture]]（含 monorepo 部署最新位置）
- **Trigger v2 coexistence:** [[concepts/dream-rec-trigger-v2-coexistence]]
- **Branch:** https://github.com/cdotlock/moonshort-backend/tree/feat/dream-rec-monorepo
- **Backend deploy 手册:** `docs/operations/2026-05-14-production-deployment-and-debug-handover.md`（Railway + Supabase + Cloudflare 形态权威说明）
