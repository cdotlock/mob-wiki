---
title: Production Pipeline — Two-Phase IDE Submit + Admin Activate
tags: [backend, ide, release, manifest, admin]
sources: [raw/2026-05-30-backend-production-pipeline-two-phase.md]
created: 2026-05-30
updated: 2026-05-30
---

2026-05 在 [[entities/lunaverse-backend]] 上线的 "Plan A + C1" 重构：把单阶段 "IDE 一键 publish 上线" 改成两阶段 **submit (IDE) → activate (admin)**，分离录入与对玩家可见，错版可 reject / rollback。配套大量 schema 收敛（`NovelDraftAsset` / `Novel.status` / `NovelCharacter.voiceId` / `characterBible` 全部移除），统一 manifest 入口写所有素材 + 语音 + episode + prompt 元信息。源文件契约：[`docs/ide-production-pipeline-migration.md`](https://github.com/cdotlock/lunaverse-backend/blob/main/docs/ide-production-pipeline-migration.md) + [`docs/operations/production-manifest-supabase-db.md`](https://github.com/cdotlock/lunaverse-backend/blob/main/docs/operations/production-manifest-supabase-db.md)。

## 为什么改

旧流程的核心问题：IDE 一调 publish 就把 L1（玩家可见字段）原地覆盖，没有人工审核闸；语音 / draft asset 走独立旁路 PATCH 路由，与 release 绑定关系松散；多套字段（`Novel.status` / `NovelCharacter.voiceId` / `NovelDraftAsset`）记录"当前是什么"，互相之间真相不一致。

新流程的核心 invariant：
- **唯一真相**：`Novel.activeReleaseId` 指向当前 live release，所有 L1 都由 activate 时从 L2 manifest re-materialize 出来。
- **录入与可见性分离**：submit 只写 L2 snapshot，admin 一手 activate 才动 L1。
- **不可绕过 service**：raw SQL 改 `activeReleaseId` 会让 L1 drift；唯一修复路径是跑 `scripts/sync-active-release.ts`（内部走 activate 的同一份 re-materialize）。

## L1 / L2 / L3 分层

| 层 | 写入方 | 内容 | 玩家代码读 |
|---|---|---|---|
| **L1** live | `activateRelease` | `Novel.title/coverUrl/synopsis`、`Episode.jsonUrl/lsUrl/contentHash`、`NovelCharacter.{displayName,role,avatarUrl,isProtagonist}`、唯一一行 `CharacterVoiceProfile.isActive=true` | ✅ |
| **L2** snapshot | `submitRelease` | `NovelProductionRelease.manifestJson`、`NovelAsset`、`CharacterAsset`、`EpisodeAssetUsage`、`PromptRun`、`CharacterVoiceProfile`（含 inactive 行） | admin 审核用 |
| **L3** pointer | `activateRelease` / `rollbackToRelease` | `Novel.activeReleaseId` | 唯一 "what's live" 真相 |

L2 只增不改；L1 由 activate 全量 re-materialize；recover 也走同一条路径。玩家可见性 invariant：`NOT archived AND activeReleaseId IS NOT NULL`。submit 不 activate → novel 留在草稿，玩家看不到。

## Release 状态机

`NovelProductionRelease.status` 只有 4 个值：

- **`pending`** — IDE 提交后默认；admin 可 activate（→ `live`）或 reject（→ `failed`）
- **`live`** — 当前 active；`Novel.activeReleaseId` 指向它
- **`superseded`** — 被新 live release 替代；admin 可 rollback 切回（重新走 activate）
- **`failed`** — admin reject 过，永久不可 activate

合法转换：

```
pending ──activate──▶ live ──supersede──▶ superseded ──activate(rollback)──▶ live
pending ──reject──▶ failed (终态)
```

约束：只有 `pending` / `superseded` 可 activate（`ReleaseTransitionError`, code `2010`）；只有 `superseded` 可 rollback 到；只有 `pending` 可 reject。

## IDE 调用的唯一接口：submit

```
POST /api/admin/novels/{novelId}/production/releases
Body: { "manifest": <NovelProductionManifest> }
```

| 项 | 值 |
|---|---|
| Auth | `requireAdmin` — HMAC cookie `noval_admin`（暂时唯一被接受的身份；service token 路径未落地） |
| `createdBy` | 从 admin 身份取（当前硬编码 `"admin"`），IDE body 里写了也忽略 |
| Idempotency | `(novelId, manifest.release.idempotencyKey)`（见下） |

成功 `data`：

```jsonc
{
  "releaseId": "clx…",          // NovelProductionRelease.id
  "status": "pending",          // ALWAYS "pending" on success — 不是 "live"
  "manifestHash": "sha256-hex",
  "idempotent": false,          // true = 同 key 同 manifest 的重放
  "counts": { "assets": {...}, "characters": {...}, "episodes": {...}, "voiceProfiles": {...} },
  "warnings": []
}
```

错误码（HTTP 200，业务 code 非零）：
- `1xxx` / `1001` — 参数 / cross-reference validation 失败（manifest 修了再发）
- `2008` — `IdempotencyConflictError`：同一个 `idempotencyKey` 来了不同 `manifestHash` / `releaseKey`，**不覆盖**已有 release；要改 manifest 内容**必须**铸新 key
- `2001` — Novel 找不到（罕见：submit 自动建草稿 novel）
- `2002` / 401 — auth 缺失

## Manifest 结构

`NovelProductionManifestSchema`（**strict**：未知 key 直接拒）：

| Field | Notes |
|---|---|
| `version` | `1` 字面量 |
| `novel` | `{ id, title, subtitle?, description?, language, coverAssetLocalId? }` — `id` 必须等于路由 `novelId` |
| `release` | `{ releaseKey, idempotencyKey, source: "ide", createdAt, ideVersion? }` |
| `assets[]` | OSS 文件 + `localId` 做 join key（`kind` 枚举：`cover` / `character_image` / `bg` / `cg` / `music` / `sfx` / `episode_json` / `ls` / `tts_audition_audio`） |
| `characters[]` | `slug` 为 join key；`role: MC \| lead \| supporting \| minor`；可挂 per-look `assets[]` |
| `episodes[]` | `episodeId` + `branchKey` + `seq` + `jsonAssetLocalId` + `assetUsage[]`（usageKind ↔ 必须的 asset.kind 匹配） |
| `voiceProfiles[]` | 直接落 `CharacterVoiceProfile`（**isActive=false** on submit）；activate 时翻一行 isActive=true |
| `promptRuns[]` | Langfuse trace 元信息（`promptName / promptVersion / traceId / inputHash / outputHash`） |

所有 cross-section reference 都走 `localId` / `slug`，提交前 `validateProductionManifestReferences` 全部预校验，任何 dangling / kind mismatch / duplicate / 跨小说引用都报 `code 1001`（msg 是 joined error list），**任何 DB 都不动**。

## Idempotency 契约

- Identity = `(novelId, idempotencyKey)`
- 首次 submit 落 `manifestHash` + `releaseKey` + `idempotencyKey`
- **同 key + 同 manifest** ⇒ no-op 成功（`idempotent: true`，counts 全 0，返回原 `releaseId`）；网络重试安全
- **同 key + 不同 manifest** ⇒ 报 `2008`，不覆盖
- **要发改了的 manifest，必须铸新 `idempotencyKey` + `releaseKey`**
- `manifestHash` 由服务端按 canonical form（key 排序、`undefined` 丢弃）算，IDE 不需要自己算

## Admin 操作（IDE 不能调）

REST 同一份 service 调用；CLI 等价命令在 [`scripts/release-cli.ts`](https://github.com/cdotlock/lunaverse-backend/blob/main/scripts/release-cli.ts)：

| 操作 | 路由 | CLI 等价 |
|---|---|---|
| activate | `POST .../releases/{releaseId}/activate` | `pnpm release-cli activate <releaseId>` |
| rollback | `POST .../releases/{releaseId}/rollback` | `pnpm release-cli rollback <novelId> <targetId>` |
| reject | `POST .../releases/{releaseId}/reject` body `{reason}` | `pnpm release-cli reject <releaseId> --reason "..."` |
| list | `GET .../releases/list` | `pnpm release-cli list <novelId>` |
| diff | `GET .../releases/{releaseId}/diff?against={otherId}` | `pnpm release-cli diff <releaseId> --against <otherId>` |
| activate voice profile | `POST .../characters/{slug}/voice-profiles/{profileId}/activate` | — |

`--by` flag 默认 `cli:$USER`，落 `activatedBy` / `rejectedBy` 审计字段。

## 删 / 弃 / 改

- **删除** `NovelDraftAsset` 表 — 折进 `NovelAsset`，没有独立 draft-asset 上传 endpoint。素材一律塞 `manifest.assets[]`，bind 到 release。
- **删除** `Novel.status` 字段 — 替成 `Novel.archived` (bool) + `Novel.activeReleaseId`。"这本上线了吗" = `activeReleaseId != null AND NOT archived`。
- **删除** `NovelCharacter.voiceId` — 语音活到 `CharacterVoiceProfile`，partial unique index `idx_character_voice_profile_active` 保证每角色至多一行 active；玩家代码读语音走 `app/lib/get-active-voice.ts`。
- **删除** manifest 的 `characterBible` 字段 — 内部 rename 成 `characterArcs`（详见 [[concepts/novel-dream-artifact]]），manifest 不再吃。
- **删除** `PATCH /api/admin/novels/{id}/voices`（narrator + MC 语音）— deprecated，返 `X-Deprecated` / `Deprecation` / `Sunset` 头；语音走 `manifest.voiceProfiles[]`。
- **删除** `PATCH /api/admin/characters/{characterId}/voice` — deprecated 同上；非 null `voiceId` 直接忽略，response 仅 echo 当前 active profile 解析出来的值。

## 玩家可见性故障恢复

`Novel.activeReleaseId` 是唯一真相。raw SQL 改它会让 L1 drift。修复：

```bash
pnpm tsx scripts/sync-active-release.ts <novelId>     # 单本
pnpm tsx scripts/sync-active-release.ts --all          # 所有挂着 activeReleaseId 的 novel
pnpm tsx scripts/sync-active-release.ts --all --dry-run
```

脚本在内部走 activate 的同一份 re-materialize 逻辑，不创建新 release、不动 status。

## IDE 端配套改动

[[entities/lunaverse-ide]] 侧在同期同步改成两阶段：
- preview / publish 走 submit endpoint
- "submitted — pending admin review" 文案替代 "published"
- 语音设计从直接 PATCH 改成进 manifest `voiceProfiles[]`（per-character voice casting workbench + audition cache + bible voice anchors）
- preview gate publish on character voices 完整 + 自动给配角分发

## 端到端验收

```bash
# DB 结构层
DIRECT_URL="$DIRECT_URL" pnpm db:assert-contracts

# 跨小说引用 + OSS 复用行为
DIRECT_URL="$DIRECT_URL" pnpm smoke:production-manifest-db

# 全 service 流程（submit → activate → rollback → reject，会留测试 novel）
ALLOW_PRODUCTION_RELEASE_SERVICE_SMOKE=yes pnpm smoke:production-release-service
```

## 相关

- [[entities/lunaverse-backend]] — 实施载体
- [[entities/lunaverse-ide]] — submit 上游
- [[concepts/supabase-backend-bootstrap]] — DB 落地的 Supabase fresh bootstrap 流程
- [[concepts/villain-season-demo]] — 第一本走全两阶段流程的双语 demo
- [[concepts/novel-dream-artifact]] — characterArcs rename 的上游 spec
