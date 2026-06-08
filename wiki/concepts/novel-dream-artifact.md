---
title: NovelDreamArtifact — Dream-Only LLM Artifact Sidecar Table
tags: [lunaverse-backend, dream, schema, novel, refactor]
sources: [raw/2026-05-24-novel-dream-artifact-extraction-design.md]
created: 2026-05-24
updated: 2026-05-24
---

1:1 sidecar of `Novel` holding the dream-only LLM-derived artifacts (`characterArcs`, `assetMapping`) that used to be inline columns on the main table. Landed 2026-05-24 to separate admin-maintained authoritative data from dream-pipeline-regenerable derived data, eliminate the V2-vs-V3 naming ambiguity in `characterBible` (renamed to `characterArcs` — the field actually carries V3-style character arcs, not V2 descriptive bios), and add per-artifact audit metadata. See [[entities/lunaverse-backend]] for the host project; [[concepts/dreaming-universe]] for the consuming pipeline.

## Why extract

Three load-bearing motivations:

1. **Authoritative ≠ derived**. `Novel` was mixing admin-maintained columns (`title / coverUrl / tagline / status / dreamEnabled / ...`) with LLM-regenerable derived JSON (`characterBible / assetMapping`). Admin tools had no way to tell which fields a `POST /character-arcs/regenerate` would silently overwrite. The sidecar makes the boundary structural.
2. **Audit gap**. The old `Novel.characterBible` was a bare `Json` column — no `promptVersion`, no `generatedAt`, no `sourceEpisodeHash`. Debugging a bad arcs generation required digging through logs. The sidecar adds `characterArcsMeta` / `assetMappingMeta` JSON blobs for cheap per-row audit context (not queried, not indexed, admin-eyes-only).
3. **Name ambiguity**. `characterBible` was V2 terminology meaning "descriptive cast bios". V3 (2026-05-02) reused the field name but inverted the semantics to "character arcs across the story". Coexisting with `NovelCharacter` (the per-novel chat-contact registry), the three terms produced reader confusion. `characterArcs` is unambiguous and orthogonal to `NovelCharacter`.

## Schema

```prisma
model NovelDreamArtifact {
  id                String   @id @default(cuid())
  novelId           String   @unique
  characterArcs     Json     @default("{}")
  assetMapping      Json     @default("{}")
  characterArcsMeta Json?
  assetMappingMeta  Json?
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  novel Novel @relation(fields: [novelId], references: [id], onDelete: Cascade)
}
```

| Field | Holds | Was |
|---|---|---|
| `characterArcs` | LLM-derived per-character arc descriptors used by dream-agent planner / writer | `Novel.characterBible` |
| `assetMapping` | Episode-aggregated `{ kind: { name: { variant: url } } }` map; full-URL form | `Novel.assetMapping` |
| `characterArcsMeta` | `{ promptVersion, generatedAt, sourceEpisodeHash, keyCharSlugs }` | (new) |
| `assetMappingMeta` | `{ generatedAt, sourceEpisodeHashes }` | (new) |

**Lazy-default semantics**: the row may be absent. Readers must treat absence as `{ characterArcs: {}, assetMapping: {} }`. Writers always use `prisma.novelDreamArtifact.upsert`. The `onDelete: Cascade` relation sweeps the sidecar whenever a Novel is deleted, so no separate cleanup is needed.

**cacheKey impact**: preheat cacheKey formula unchanged — still `sha256(characterArcs)` mixed with other input hashes. Meta blobs are explicitly excluded from cacheKey (they're metadata about the data, not data the consumer reads).

## API rename

Coordinated path rename — no alias kept (trunk-based; no external consumers):

| Old | New |
|---|---|
| `GET /api/internal/novels/:id/character-bible` | `GET /api/internal/novels/:id/character-arcs` |
| `POST /api/admin/novels/:id/character-bible/regenerate` | `POST /api/admin/novels/:id/character-arcs/regenerate` |
| Response field `characterBible` | `characterArcs` |
| Preheat bundle field `characterBible` | `characterArcs` |

## Migration shape

Three-step roll-out, see [source](../../raw/2026-05-24-novel-dream-artifact-extraction-design.md) §3 for the full SQL:

- **Step 1**: create `NovelDreamArtifact` + backfill from `Novel.characterBible` / `Novel.assetMapping`. Old columns untouched, old code keeps working. (Landed 2026-05-24, Phase 1.)
- **Step 2**: switch all readers and writers to the sidecar, rename API paths, propagate `characterArcs` through dream-agent prompts/types. **Release-unit constraint**: all Step 2 commits must push together to avoid "preheat writes new / API reads old" inconsistency windows. (Landed Phases 2-4.)
- **Step 3**: `DROP COLUMN Novel.characterBible / Novel.assetMapping` — deferred until Step 2 observed stable in prod, no rollback risk.

## What was deliberately not done

- **Don't split `NovelCharacter`**. Its three responsibilities (ingest-derived registry, admin business-rule control, chat contact index) are data-coupled — splitting forces a join on every consumer. The naming ambiguity came from `characterBible`, not `NovelCharacter`.
- **Don't move `dreamEnabled` to the sidecar**. It's admin-controlled, same semantic class as `viewCount / likeCount`. Belongs on the main table; moving forces an extra join in `dream-trigger-service` with zero readability gain.
- **Don't keep API alias paths**. Trunk-based project, no external API consumers. One-shot cut is cleanest.

## Audit field shape

```ts
type CharacterArcsMeta = {
  promptVersion: string;       // Langfuse prompt version
  generatedAt: string;          // ISO 8601 UTC
  sourceEpisodeHash: string;    // sha256 of concatenated source episode contentHash (in seq order)
  keyCharSlugs: string[];       // slugs chosen by §6.4 Step 1, retained for debug
};

type AssetMappingMeta = {
  generatedAt: string;
  sourceEpisodeHashes: Record<string, string>;  // episodeId -> contentHash that contributed
};
```

Written by `regenerateCharacterArcsStep` (preheat-service) and `episode-bulk-insert-service` in the same transaction as the corresponding data field.

## Related

- [[concepts/dreaming-universe]] — pipeline that consumes `characterArcs` for planner / writer / arc-reviewer prompts
- [[concepts/dream-trigger-v2-mechanical]] — sister-concept: when to trigger a dream; the trigger doesn't touch `characterArcs` but the v2-mechanical Out-of-Scope note references this refactor
- [[entities/lunaverse-backend]] — host project
