---
title: Gateway-bypass + Origin lockdown cutover 2026-06-10
updated: 2026-06-10
---

> lunaverse-backend 2026-06-10：nginx gateway 从服务路径退场 + Origin lockdown 激活。一次窗口内完成代码合并、Railway custom-domain swap、Cloudflare Transform Rules、DNS CNAME 重指，全程 API 操作。

## 背景

- 拓扑（之前）：`Cloudflare → gateway(nginx) → app`。nginx 只剩三件事 —— 裸 `/api/*` 代到 `/web/api/*`、裸页面 302 → `/web/*`、空 Cocos 静态托管 —— 每件都有去向（详见 [`docs/operations/2026-06-10-gateway-bypass.md`](https://github.com/cdotlock/lunaverse-backend/blob/main/docs/operations/2026-06-10-gateway-bypass.md)）。
- Origin lockdown 原方案：在 nginx 拒掉缺 `X-Lunaverse-Origin-Verify` 头的请求（branch `claude/condescending-goldwasser-fb8797` commit `75f361b3`）。gateway 退场后必须搬家到 Next middleware。
- 触发：`fix/db-connection-exhaustion` 与 `codex/ls-refactor-doc-cleanup-8090` 已上 main 并 6543 切换部署成功，留下 main 上的 gateway-bypass 代码（commits `526ed623` / `584dbd43` / `59a71c37`）和 nginx 原版 origin lockdown 各自待执行。

## 代码层（先落地，再切换）

| commit | 内容 |
|---|---|
| `c1b9d13e` (本次新增) | `app/lib/origin-verify.ts` (fail-open + timing-safe `timingSafeEqual`) + middleware 接入；豁免 `/api/health`（Railway 健康探活）与 `/api/internal/*`（dream-agent 经 `app.railway.internal` 私网回调，本来就有 `Bearer CHEAT_TOKEN`）。`.env.production.example` 加 `ORIGIN_VERIFY_SECRET` 占位；runbook Appendix E 同步。 |
| `8daaf449` | runbook Appendix E 加 Status 段：rule id / zone id / 4/4 验证证据。 |

## 切换执行（2026-06-10 ~14:30-15:10 UTC）

### Step 0 — CF Transform Rule：URL rewrite

```http
PUT /zones/3e270cfe6a68f4412aba66729c5561c8/rulesets/phases/http_request_transform/entrypoint
{
  "rules": [{
    "action": "rewrite",
    "action_parameters": {"uri": {"path": {"expression": "concat(\"/web\", http.request.uri.path)"}}},
    "expression": "(http.host eq \"app.moonshort.ai\" and starts_with(http.request.uri.path, \"/api/\"))",
    "enabled": true
  }]
}
```

- rule id：`6c46a34f0a0048eeb1756ee584e62c35`
- 旧 nginx 链路下无害（`/web/` location 透传），可以**在 swap 前先开**，验证 `app.moonshort.ai/api/health` 单请求 200 无 redirect、POST `/api/auth/login` 200（业务 envelope，非 3xx 即可证 Stripe webhook 安全）。

### Step 1 — Railway custom-domain swap（原子三步，~9s）

`customDomainCreate` 不允许同一域名同时挂两个服务（事先实测得 `INTERNAL_SERVER_ERROR`），所以必须 delete → create → DNS 重指连续打。

| t | 操作 | 结果 |
|---|---|---|
| T+0 | `customDomainDelete(id=3f7515ae-68f5-4fd4-a8dd-fa76b20422d9)` on gateway | gateway 放弃 `app.moonshort.ai` 的 claim，gateway 旧 target `lh683s50.up.railway.app` 失效 |
| T+1 | `customDomainCreate(domain=app.moonshort.ai, serviceId=23b28467-3247-4332-9633-bcf83ef83f2c)` on app | 新 custom-domain id `57194a41-41f1-49c4-b16f-3fdbac77739e`，新 CNAME target `y1p5adun.up.railway.app` |
| T+2 | `PATCH /zones/$ZONE/dns_records/730cc379c22ad8c3a9162328ab4c8e6c` content → `y1p5adun.up.railway.app` | CF DNS 立即生效（Proxied TTL=1） |

**实测探针**：T+5..T+35s 15×2s 健康探针 14/15 返 200，唯一一次失败是本地 LibreSSL syscall 抖动而非生产问题；gateway nginx 自 15:07:22 起无新流量。

### Step 2 — Origin lockdown 激活

```http
PUT /zones/$ZONE/rulesets/phases/http_request_late_transform/entrypoint
{
  "rules": [{
    "action": "rewrite",
    "action_parameters": {"headers": {"X-Lunaverse-Origin-Verify": {"operation": "set", "value": "<openssl rand -hex 32>"}}},
    "expression": "(http.host eq \"app.moonshort.ai\")"
  }]
}
```

- rule id：`fd17e9795dff4fb28d8d7d9cd56af026`（phase `http_request_late_transform`，**与 step 0 不同 phase**，header injection 只在 late_transform 才生效）
- 同 secret 设入 **app 服务**（不再是 gateway）的 `ORIGIN_VERIFY_SECRET` env，触发 redeploy。
- 4/4 验证：
  - 经 CF `app.moonshort.ai/api/health` → 200 healthy ✓
  - 直连 `*.up.railway.app/web/api/novels` no header → 403 `{code:2403}` ✓
  - 直连 `*.up.railway.app/web/api/health` → 200（豁免）✓
  - 直连 `*.up.railway.app/api/internal/dream-agent-health` → 200（豁免，自带 CHEAT_TOKEN 鉴权）✓
  - 直连 `*.up.railway.app/web/api/novels` 带正确 header → 200（CF 等价路径）✓

## 关键经验

1. **`customDomainUpdate` 只能改 targetPort，不能换 serviceId** —— 实测 GraphQL schema 直接确认。所以 swap 必须 delete + create。
2. **DNS 端要带 Proxied** —— PATCH dns_record 时必须明传 `"proxied": true`，否则 CF 把 record 降为 grey-cloud（绕过 CF 边缘，失去 Transform Rule 与 origin 隐藏，全套保护全废）。
3. **header injection 是 `http_request_late_transform` phase，URL rewrite 是 `http_request_transform`** —— 同 phase 同时塞俩 rule 会失败，要分两次 PUT。
4. **Next basePath=/web 时 middleware matcher 的相对性** —— `middleware.ts` 的 `matcher: ["/api/:path*"]` 在生产 basePath 下实际匹配 `/web/api/:path*`。所以直连 origin 即使被 in-app `redirects()` 307 到 `/web/api/*`，middleware **会** 在跳转后的请求上生效，行为 = 拒。验证时必须 curl `-L` 跟随 redirect 或直接打 `/web/api/...`，否则会误判 "guard 没生效"。
5. **`assert-prod-env` 救命**：本次部署的第一个 deploy run 因 `CHEAT_WRITE=true` 被 boot-time assertion 拒启动。Security hardening 的 prod env 断言生效。`ADMIN_ENABLE_CHEATS=true` 是有意保留的（read tier，dream-agent 探活 + deploy smoke 需要），但 `CHEAT_WRITE` 必须 false。

## 引用

- 切换手册：[`docs/operations/2026-06-10-gateway-bypass.md`](https://github.com/cdotlock/lunaverse-backend/blob/main/docs/operations/2026-06-10-gateway-bypass.md)
- DB 连接修复（同期落地的姊妹工作）：[[concepts/db-connection-budget]]
- 安全加固主线：[[concepts/backend-security-hardening-2026-06]]
- Runbook Appendix E：[`docs/runbook.md`](https://github.com/cdotlock/lunaverse-backend/blob/main/docs/runbook.md#appendix-e-origin-lockdown)

## 待办（仅 ≥24h 观察期后做的清理 commit）

- 删 Railway gateway 服务（id `0e48f07a-1f7a-4ab0-9a33-0c6ff820ab7a`）
- 删 CI 里 gateway deploy job
- 删 repo `nginx/`、`Dockerfile.railway-gateway`
- runbook 服务表 / §400 header 条目 / BASE 用法处给 `/api/health` 加 `-L` 或换 `/web/api/health`
- 删原 nginx 版本 origin lockdown 占位（已迁 middleware，仅 nginx 模板里有，伴随 `nginx/` 整目录删除一并消失）
- Stripe live-mode 切换前用户在 dashboard 确认无 webhook 直接 hit 裸 `/api/stripe/webhook`，有则改 `/web/api/stripe/webhook` 或依赖 Transform Rule
