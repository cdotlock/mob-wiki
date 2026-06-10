---
title: lunaverse-backend 生产安全加固（2026-06-10）
updated: 2026-06-10
sources:
  - raw/2026-06-10-lunaverse-backend-security-hardening.md
---

# lunaverse-backend 生产安全加固（2026-06-10）

2026-06-10 合入 main（merge `b8cd95a7`）的四轨安全加固。权威文档在 backend 仓：spec `docs/superpowers/specs/2026-06-10-production-security-hardening-design.md`、plan 同目录、轮换 runbook `docs/security/secret-rotation-2026-06.md`。

## 四轨内容

- **Track A — Secret 轮换工具链**（P0-SEC-001）：`.env.prod` 曾入库（`git show e0098d54:.env.prod` 至今可读）。处置选 **轮换 + 登记**（A2），不重写 history（仓库 private；**若转 public 必须先 filter-repo 清史**）。交付 `scripts/security/audit-leaked-secrets.sh`（railway env 哈希对比，逐 key 输出 LIVE/DEAD/ABSENT，不打印值）+ 轮换 runbook。已验证：泄露的 Stripe key 是 **test-mode**（`sk_test_`），live key 从未入库。**轮换执行仍待用户**（需 railway login + Stripe dashboard）。
- **Track B — Auth 限流 + admin fail-closed**（P1-SEC-002）：生产无 Redis（pgmq 取代），限流用 **Postgres fixed-window**（`RateLimitCounter` 表 + 原子 INSERT…ON CONFLICT，fail-open）。login IP 10/5min（全计）、login 账号 5/15min（只计失败）、register IP 5/h、admin IP 5/15min；超限 HTTP 429 + code 1429（API-SPEC 契约增补待审批）。admin-auth 移除 `JWT_SECRET ?? "dev-secret"` fallback（fail closed）。
- **Track C — CORS allowlist + 安全 header**（P1-SEC-003）：通配 `Access-Control-Allow-Origin: *` 全量移除，CORS 收口到 middleware（allowlist 在 `app/lib/cors.ts`，OPTIONS 预检 middleware 短路）；站点级 nosniff / `X-Frame-Options: SAMEORIGIN`（minigame 同源 iframe，DENY 会打破）/ Referrer-Policy / HSTS（仅生产）。web 前端同源 + Cocos/CLI 无 Origin → 实际零破坏面。
- **Track D — 防复发 guardrail**：boot 断言 `app/lib/assert-prod-env.ts`（fatal：`CHEAT_WRITE=true`、`ENABLE_MOCK_TOPUP=true`、缺 JWT_SECRET/ADMIN_PASSWORD、cheats 开但 CHEAT_TOKEN <32 字符；逃生阀 `PROD_ENV_ASSERT_DISABLE`）+ gitleaks CI gate（`.gitleaks.toml` 对编译剧本 JSON 做 path allowlist，凭据类只允许 per-fingerprint 豁免；首跑已绿）。

## 关键决策与发现

1. **生产 read-tier cheats 是硬依赖**：deploy workflow 的 dream smoke 用 `PRODUCTION_CHEAT_TOKEN` 探活 `/api/internal/dream-agent-health`，dream-agent 回调同走 `CHEAT_TOKEN`。旧文档"生产 `ADMIN_ENABLE_CHEATS=false`"与现实矛盾，已全量修正——正确不变量是 **enabled ⇒ token 强 + write 关**，由 boot 断言强制。
2. **轮换优先级按爆炸半径排序**：ADMIN_PASSWORD → 内部 bearer（注意 `CHEAT_TOKEN` ↔ GitHub secret `PRODUCTION_CHEAT_TOKEN` 配对）→ 上游 key → Stripe（test-mode，预期 DEAD）→ JWT_SECRET（全玩家登出，择时）。
3. **遗留待办（用户侧）**：跑 audit 脚本确认 LIVE/DEAD 并执行轮换；API-SPEC.md 增补 1429（七契约审批流）；轮换后把断言的强度 warn 提为 fatal。

相关：[[entities/lunaverse-backend]]、[[concepts/railway-production-deploy]]、[[concepts/supabase-backend-bootstrap]]、[[concepts/db-connection-budget]]
