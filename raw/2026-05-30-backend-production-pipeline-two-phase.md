---
name: backend-production-pipeline-two-phase
description: Backend two-phase publish (IDE submit + admin activate) — mirror of moonshort-backend's IDE migration doc + Supabase manifest runbook
source_repo: cdotlock/moonshort-backend
source_files:
  - docs/ide-production-pipeline-migration.md
  - docs/operations/production-manifest-supabase-db.md
fetched: 2026-05-30
status: source-of-truth-mirror
---

# Production Pipeline Two-Phase — Source Mirror (2026-05-30)

This raw record mirrors the two upstream backend docs that established the 2026-05 "Plan A + C1" two-phase publish refactor. Wiki synthesis lives at [[concepts/production-pipeline-two-phase]].

## Source files

- IDE migration guide: [`docs/ide-production-pipeline-migration.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/ide-production-pipeline-migration.md)（≈318 行；IDE 团队迁移 spec，commit `cf737dfa..f6101686`）
- Supabase DB runbook: [`docs/operations/production-manifest-supabase-db.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/operations/production-manifest-supabase-db.md)（≈250 行；DB 层 invariant + bootstrap）

## Quoted key invariants

> **Publishing is now TWO-PHASE.** The IDE's "publish" = **SUBMIT** a release. Submit creates a release in `pending` status and writes a snapshot. **The novel does NOT go live.**
> A **human admin** then **ACTIVATES** the pending release from the admin console. Activation is what materializes the player-visible fields (cover, episode `jsonUrl`, avatars, voice). **The IDE no longer controls go-live.**

> 数据库不存音频/图片/JSON 大文件本体；大文件在 OSS，数据库存 `ossKey`、`ossUrl`、`contentHash`、角色绑定、episode 使用关系、Breeze `voiceId`、Langfuse trace/prompt 元信息。

> **玩家可见性 invariant**：`NOT archived AND activeReleaseId IS NOT NULL`。submit 完不 activate → novel 留在草稿，玩家看不到。

## Removed / deprecated

- `NovelDraftAsset` table folded into `NovelAsset`
- `Novel.status` replaced by `Novel.archived` + `Novel.activeReleaseId`
- `NovelCharacter.voiceId` replaced by `CharacterVoiceProfile` (unique active per character via partial index `idx_character_voice_profile_active`)
- `characterBible` renamed to `characterArcs`, moved to `NovelDreamArtifact`
- `PATCH /api/admin/novels/:id/voices` — deprecated (`X-Deprecated: true`)
- `PATCH /api/admin/characters/:characterId/voice` — deprecated, ignores `voiceId` in body

## Idempotency rule

- Identity = `(novelId, manifest.release.idempotencyKey)`
- Same key + same manifest ⇒ no-op success (`idempotent: true`)
- Same key + different manifest ⇒ `IdempotencyConflictError` (`code 2008`)
- To publish changed content: mint NEW `idempotencyKey` + `releaseKey`

For full ingestion, read upstream files directly via the links above. Synthesis page extracts and structures the operational rules.
