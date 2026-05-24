# Novel Dream Artifact 抽表 — Design Spec

**日期**：2026-05-24
**作者**：cdotlock + Claude
**状态**：施工 spec
**前置阅读**：
- [`../../mss-refactor/DATA-MODEL.md`](../../mss-refactor/DATA-MODEL.md) §Novel — 当前权威契约
- [`../../../prisma/schema.prisma`](../../../prisma/schema.prisma) Novel / NovelMultiplayerConfig / NovelCharacter — 实际形状（NovelMultiplayerConfig 是本次抽表的现成参照）
- [`2026-05-22-novel-schema-v2-design.md`](2026-05-22-novel-schema-v2-design.md) §3 — multiplayerScenario 抽表的同型先例
- [`2026-05-02-dream-agent-v3-foundation-design.md`](2026-05-02-dream-agent-v3-foundation-design.md) §2.1 §6.4 §8 — characterBible/assetMapping 生成与消费契约（本 spec 不改语义，只改存放位置）
- [`../../architecture/migration-policy.md`](../../architecture/migration-policy.md) — migration = incremental patch（**不**支持 fresh-DB replay）

---

## 0. 摘要

把 `Novel.characterBible` 和 `Novel.assetMapping` 两个 dream-only 派生 JSON 列搬出 Novel 主表，集中放到新的 `NovelDreamArtifact` 表（1:1 关联）。同时把 `characterBible` 改名为 `characterArcs`（消除 V3 语义反转遗留的误导名），并把对应 API 路径与代码变量同步改名。`dreamEnabled` 留在 Novel（admin 控制的权威开关，非派生数据）。

**为什么做**：

1. **权威 vs 派生分家**：Novel 主表当前混存了 admin 维护的权威数据（title/coverUrl/tagline/...）和 dream LLM 派生的可重生产物（characterBible/assetMapping），admin 工具看不出哪些字段是"改了会被下次 preheat 覆盖"。抽表后语义边界清晰。
2. **审计能力上线**：当前 `Novel.characterBible` 只是一个裸 Json，没有 `promptVersion / generatedAt / sourceEpisodeHash` 等元信息——出了 bug 只能翻日志。抽表后顺手把元信息装进 `characterArcsMeta` blob。
3. **命名歧义消除**：`characterBible` 这名字是 V2 遗留——V3 把语义从"描述性人设"反转成"角色弧光"还保留了字段名，跟 `NovelCharacter`（per-novel 角色注册表）并存，三层歧义叠在一起。改名 `characterArcs` 后语义直白，跟 NovelCharacter 也不冲突（一个是"角色注册"，一个是"角色弧光"）。

**为什么不做**：

- **不拆 NovelCharacter**：调研显示它的三类职责（ingest 派生注册、admin 控制业务规则、chat 联系人索引）在数据上紧耦合（admin 给 slug 打 `isChattable` 必然依赖 ingest 先建出 slug），拆开会让所有 chat / dream / admin 查询多一次 join，而当前 6 字段单表完全够用。命名歧义来自 characterBible，不是 NovelCharacter 本身。
- **不搬 dreamEnabled**：admin 控制的开关，跟 viewCount/likeCount 同性质，归 Novel 合理；搬走会让 dream-trigger-service 多 join 一次拿不到收益。
- **不保留 API 旧路径 alias**：项目 trunk-based，无外部消费者，一刀切最干净。

规模：1 张新表 + 2 次 migration（建表+backfill / 删旧列）+ preheat-service 改 novelLoader + dream-agent client 改字段名 + 2 个 API 路径改名 + DATA-MODEL.md 契约同步 + 测试 / scripts 适配。预计 1 天。

---

## 1. 当前状态 vs 目标状态

### Novel 表

| 字段 | 现状 | 目标 | 备注 |
|---|---|---|---|
| `id` `title` `coverUrl` `status` `synopsis` `tagline` `tags` `kind` `dreamEnabled` `checkingSlots` `viewCount` `likeCount` `createdAt` `updatedAt` | ✅ | ✅ | 全部保留（权威数据） |
| `assetMapping` | ✅ Json | ❌ | **删除**，迁到 NovelDreamArtifact.assetMapping |
| `characterBible` | ✅ Json | ❌ | **删除**，迁到 NovelDreamArtifact.characterArcs（**同时改名**） |
| `multiplayerConfig` (relation) | ✅ | ✅ | 已有 1:1 模式，本次新增 1:1 同型 |

### 新增 NovelDreamArtifact 表

| 字段 | 类型 | 备注 |
|---|---|---|
| `id` | String @id @default(cuid()) | |
| `novelId` | String @unique | 1:1 with Novel |
| `characterArcs` | Json @default("{}") | 原 `Novel.characterBible`；§2.1 形态保持不变 |
| `assetMapping` | Json @default("{}") | 原 `Novel.assetMapping`；episode 聚合产物 |
| `characterArcsMeta` | Json? | `{ promptVersion, generatedAt, sourceEpisodeHash, keyCharSlugs }`，**新增**审计能力 |
| `assetMappingMeta` | Json? | `{ generatedAt, sourceEpisodeHashes }`，**新增**审计能力 |
| `createdAt` `updatedAt` | DateTime | 标准 |

关系：`novel Novel @relation(fields: [novelId], references: [id], onDelete: Cascade)`。

懒生成语义：行不存在时视同 `{ characterArcs: {}, assetMapping: {} }`；preheat 首次写入时由 `upsert` 创建。

### API 路径

| 现在 | 改名后 |
|---|---|
| `GET /api/internal/novels/:novelId/character-bible` | `GET /api/internal/novels/:novelId/character-arcs` |
| `POST /api/admin/novels/:id/character-bible/regenerate` | `POST /api/admin/novels/:id/character-arcs/regenerate` |

不保留旧 alias。响应 body 字段同步从 `characterBible` 改为 `characterArcs`。

---

## 2. Schema 设计细节

### 2.1 为什么审计字段用 Json blob 而非平铺列

- `characterArcs` 和 `assetMapping` 的元数据形态不同（前者有 LLM prompt 版本，后者没有），平铺会让 schema 一堆 nullable 列
- 元数据**只用于 admin 查看 + debug**，从不参与 query / index
- Json blob 易扩展，加新字段不需要 migration

### 2.2 characterArcsMeta 字段约定

```ts
type CharacterArcsMeta = {
  promptVersion: string;       // Langfuse prompt version that produced this artifact
  generatedAt: string;          // ISO 8601 UTC
  sourceEpisodeHash: string;    // sha256 of concatenated source episode contentHash (in seq order)
  keyCharSlugs: string[];       // slugs chosen by §6.4 Step 1, retained for debug
};
```

写入时机：`regenerateCharacterBibleStep`（preheat-service）成功生成 characterArcs 后，同事务 upsert NovelDreamArtifact 的 `characterArcsMeta`。

### 2.3 assetMappingMeta 字段约定

```ts
type AssetMappingMeta = {
  generatedAt: string;                       // ISO 8601 UTC
  sourceEpisodeHashes: Record<string, string>;  // episodeId -> contentHash that contributed
};
```

写入时机：`episode-bulk-insert-service` 完成 assetMapping 聚合后，同事务 upsert `assetMappingMeta`。

### 2.4 cacheKey 公式不变

preheat cacheKey 仍是 `sha256(characterArcs)` 等多项 hash 的组合，只是读源从 `Novel.characterBible` 改为 `NovelDreamArtifact.characterArcs`。**不引入** meta 字段进入 cacheKey（meta 是元信息，不是被消费的数据本身）。

---

## 3. 迁移策略（三步法）

### Step 1: Migration #1 — 建表 + backfill

单一 Prisma migration:

```sql
-- 1. 建表
CREATE TABLE "NovelDreamArtifact" (
  "id" TEXT PRIMARY KEY,
  "novelId" TEXT UNIQUE NOT NULL REFERENCES "Novel"("id") ON DELETE CASCADE,
  "characterArcs" JSONB NOT NULL DEFAULT '{}',
  "assetMapping" JSONB NOT NULL DEFAULT '{}',
  "characterArcsMeta" JSONB,
  "assetMappingMeta" JSONB,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL
);

-- 2. backfill：把现有 Novel 上两个字段值复制过来
INSERT INTO "NovelDreamArtifact" ("id", "novelId", "characterArcs", "assetMapping", "createdAt", "updatedAt")
SELECT
  'cldream_' || substr(md5(random()::text), 1, 24),  -- cuid-like; Prisma 后续 upsert 不会再用此 id
  "id",
  COALESCE("characterBible", '{}'::jsonb),
  COALESCE("assetMapping", '{}'::jsonb),
  NOW(),
  NOW()
FROM "Novel"
WHERE "characterBible" IS NOT NULL OR "assetMapping" IS NOT NULL;
```

代码此时不动。部署后：
- 旧代码仍读写 `Novel.characterBible / assetMapping`
- 新表已有完整数据但无读者
- 风险：极小（纯增量；旧字段仍是 source-of-truth）

### Step 2: 切代码（release-unit）

**部署节奏硬规则**：Step 2 的全部 commits 必须作为**一个 release-unit** 推送 —— 在本地把下方 11 步 commit 跑完 + `pnpm lint` / `pnpm tsc` / `pnpm build` / `pnpm smoke:all` 全绿后**一次性 push 触发部署**。不允许中间任何 commit 单独 push 上生产，否则会出现"preheat 写新表 / API 读旧表"或反之的中间不一致状态。

按依赖顺序改：

1. **schema 注册**：`Novel` model 加 `dreamArtifact NovelDreamArtifact?` relation；不删旧字段
2. **preheat-service novelLoader 接口**：`saveCharacterBible` → 改为 `saveDreamArtifact`，写 NovelDreamArtifact（upsert）；`loadNovel` 返回 `PreheatNovelMeta` 时改从 NovelDreamArtifact 读 characterArcs/assetMapping
3. **episode-bulk-insert-service**：assetMapping 写入目标改 NovelDreamArtifact（upsert）
4. **internal API**：
   - 路径 `/character-bible` → `/character-arcs`
   - 响应 body 字段 `characterBible` → `characterArcs`
   - 读源切到 NovelDreamArtifact
5. **admin API**：路径同上改名，读写源同步切
6. **dream-agent**：
   - `services/dream-agent/src/manager-tools.ts` 内变量 `characterBible` / `character_bible_json` → `characterArcs` / `character_arcs_json`
   - `services/dream-agent/src/validation.ts` 同步
   - `services/dream-agent/src/types.ts` 字段名同步
   - `services/dream-agent/prompts/*.md` 凡 prompt 模板里出现 `character_bible` 的 placeholder → `character_arcs`
7. **preheat-bundle 响应 body**：bundle 内 `characterBible` 字段→ `characterArcs`。**这是 dream-agent 主消费路径，跟 §6 的 dream-agent 子包改动同步部署**
8. **admin UI**（如有 dream regen 按钮）：路径同步
9. **测试 / scripts**：
   - `__tests__/services/dream-preheat/preheat/*.test.ts` 适配
   - `scripts/dream-triggers-e2e.ts` / `scripts/dream-preheat-bundle-smoke.ts` 适配
   - `services/dream-agent/test/fixtures/*` 适配
10. **DATA-MODEL.md 契约**：§Novel 删除 `characterBible / assetMapping` 行；新增 §NovelDreamArtifact section
11. **api-spec.md / cocos-contract**（如涉及）：路径改名

每改动 1-2 个独立单元 commit 一次（按 CLAUDE.md atomic commit 规则）。Step 2 整体跑通 `pnpm lint` / `pnpm tsc` / `pnpm build` / `pnpm smoke:all` 全绿后部署。

### Step 3: Migration #2 — 删旧列

```sql
ALTER TABLE "Novel" DROP COLUMN "characterBible";
ALTER TABLE "Novel" DROP COLUMN "assetMapping";
```

确保 Step 2 已经全量部署且观察 1 天无回滚后再跑。

---

## 4. 影响面清单

### 4.1 代码改动

| 文件 / 模块 | 改动 |
|---|---|
| `prisma/schema.prisma` | 加 NovelDreamArtifact model；Novel 加 relation；Step 3 删两个旧列 |
| `app/services/dream-preheat/preheat/preheat-service.ts` | novelLoader interface 改造 |
| `app/services/dream-preheat/preheat/character-bible.ts` | 内部模块名 / 注释更新；逻辑不变 |
| `app/services/episode-bulk-insert-service.ts` | assetMapping 写入目标改表 |
| `app/api/internal/novels/[novelId]/character-bible/route.ts` | **移动 + 改名**：→ `app/api/internal/novels/[novelId]/character-arcs/route.ts` |
| `app/api/admin/novels/[id]/character-bible/regenerate/route.ts` | **移动 + 改名**：→ `app/api/admin/novels/[id]/character-arcs/regenerate/route.ts` |
| `app/api/internal/preheat-bundle/[novelId]/route.ts` | 响应 body 字段名改名 |
| `services/dream-agent/src/manager-tools.ts` | 变量名 + context key 改名（6 处） |
| `services/dream-agent/src/validation.ts` | `checkEpisodeContinuity` 内字段名改名 |
| `services/dream-agent/src/types.ts` | type 字段改名 |
| `services/dream-agent/prompts/dream_agent__planner__system.md` | prompt 模板 placeholder 改名 |
| `services/dream-agent/prompts/dream_agent__manager__system.md` | 同上 |
| `services/dream-agent/skills/dream-character-voice/SKILL.md` | 表述更新 |
| `services/dream/production/skills/dream-arc-reviewer/SKILL.md` | 表述更新 |
| `services/dream/production/skills/dream-episode-writer/SKILL.md` | 表述更新 |
| `app/admin/novels/[id]/page.tsx` 或类似 admin UI | regen 按钮路径改名（待确认实际位置） |

### 4.2 文档改动

| 文件 | 改动 |
|---|---|
| `docs/mss-refactor/DATA-MODEL.md` | §Novel 删除 characterBible/assetMapping；新增 §NovelDreamArtifact |
| `docs/superpowers/specs/2026-05-02-dream-agent-v3-foundation-design.md` | §2.1 §6.4 §8 加 deprecation 注脚指向本 spec；字段名更新 |
| `docs/superpowers/specs/2026-05-22-novel-schema-v2-design.md` | 表格里 `characterBible` / `assetMapping` 行标注"已迁出，见 2026-05-24-novel-dream-artifact-extraction"|
| `docs/architecture/llm-backend-boundary-followup-2026-05-04.md` | 字段名更新 |

### 4.3 测试 / smoke 改动

- `__tests__/services/dream-preheat/preheat/preheat-service.test.ts`
- `__tests__/services/dream-preheat/preheat/bundle.test.ts`
- `__tests__/services/dream-preheat/preheat/cache-key.test.ts`
- `scripts/dream-triggers-e2e.ts`
- `scripts/dream-preheat-bundle-smoke.ts`
- `scripts/v3-acceptance-check.ts`
- `services/dream-agent/test/smoke-real.test.ts`
- `services/dream-agent/test/fixtures/branched-novel-fixture.ts`
- `services/dream-agent/test/fixtures/loop7-backend-fixture.ts`

均需把 fixture / 期望值里的 `characterBible` 改为 `characterArcs`，并确认 NovelDreamArtifact 行的创建/读取在测试场景下正确。

### 4.4 不受影响

- chat / 联系人系统（消费 NovelCharacter，不接触本次抽出的字段）
- cocos 前端 / 玩家公开 API（从未消费 characterBible/assetMapping）
- CLI noval（不接触 dream 链路）
- save / game-rule / action-record（消费 `checkingSlots`，留在 Novel）

---

## 5. 风险与回滚

### 5.1 主要风险

| 风险 | 缓解 |
|---|---|
| Step 2 部署后 dream-agent 容器读不到新字段名 | preheat-bundle 响应 body 改名跟 dream-agent src/prompts 改名**同一次 push** 推送（虽然 Railway 上 backend 容器与 dream-agent 容器独立滚动，dream-agent 先做兼容读即可——见 §6） |
| Step 1 backfill 漏行 | 派生数据**可重生**——admin 跑 `POST /character-arcs/regenerate` 即可重建；不是数据丢失 |
| NovelDreamArtifact 行不存在时读 null | preheat-service / API 层在 loader 里做 `?? { characterArcs: {}, assetMapping: {} }` fallback；首次写入用 upsert |
| Step 3 删列前误删 | 等 Step 2 观察 1 天无回滚再跑；删列前用 SQL 验证两列在所有 Novel 上的值已与 NovelDreamArtifact 一致 |

### 5.2 回滚策略

- **Step 1 之后** 想回滚：直接 `DROP TABLE NovelDreamArtifact`。旧字段仍在 Novel，旧代码运行正常
- **Step 2 之后** 想回滚：revert 代码 commit。新表有数据但旧字段也有（Step 1 时复制了一份），revert 后旧字段仍可用。**唯一例外**：Step 2 部署期间新生成的 characterArcs/assetMapping 只写了新表没写旧字段——这部分数据回滚后会"消失"，但派生数据可重生，跑一次 regenerate 即可
- **Step 3 之后** 想回滚：旧字段已删，无法快速回滚。**因此 Step 3 必须留观察期**

### 5.3 数据完整性验收

Step 2 完成后、Step 3 之前，在生产环境跑：

```sql
SELECT n.id,
       (n."characterBible" IS DISTINCT FROM nda."characterArcs") AS character_diff,
       (n."assetMapping" IS DISTINCT FROM nda."assetMapping") AS asset_diff
FROM "Novel" n
LEFT JOIN "NovelDreamArtifact" nda ON nda."novelId" = n."id"
WHERE n."characterBible" IS DISTINCT FROM COALESCE(nda."characterArcs", '{}'::jsonb)
   OR n."assetMapping" IS DISTINCT FROM COALESCE(nda."assetMapping", '{}'::jsonb);
```

预期返回 0 行；非 0 行需逐个核查后才能跑 Step 3。

---

## 6. dream-agent 子包协同

dream-agent 是 monorepo 内的独立 TypeScript 子包（`services/dream-agent/`，`@moonshort/dream-agent` package，自带 Dockerfile），通过 `POST /api/internal/preheat-bundle/:novelId` 从 backend 拿完整 bundle。bundle 内 `characterBible` 字段是 dream-agent prompt 模板（`prompts/*.md`）的输入变量，由 `src/manager-tools.ts` 注入 context。

虽然两个子包在同一个 monorepo 里、同一次 `git push` 触发部署，但 Railway 上 backend 容器与 dream-agent 容器**独立滚动重启**，部署期间会短暂出现"新 backend + 旧 dream-agent"或反之。所以即便代码 atomic，运行时仍需兼容期。

**协同点**：
- `services/dream-agent/prompts/dream_agent__planner__system.md` 等 prompt 模板里的 `{{character_bible_json}}` placeholder → `{{character_arcs_json}}`
- `services/dream-agent/src/manager-tools.ts` 装填 context 的 key 名同步改

**部署顺序（定）**：

1. **commit 1（dream-agent 兼容读上线）**：`services/dream-agent/src/manager-tools.ts` / `validation.ts` 内读 `bundle.characterArcs ?? bundle.characterBible`，prompt 模板新增 `{{character_arcs_json}}` 占位符同时保留旧 `{{character_bible_json}}`（用 `??` 兜底）。这一 commit 单独 push 部署，验证 dream-agent 容器无 regression。
2. **commit 2-N（backend release-unit）**：按 §3 Step 2 11 步改完（preheat-bundle 响应 body 切到 `characterArcs`，旧字段不再产出），一次性 push。
3. **commit 末（清兼容）**：dream-agent 清掉 `?? characterBible` 兜底 + 删除旧 prompt 占位符。

理由：backend 改动面大（11 步），让 dream-agent 先兜底 1 个独立 commit 就能让整个 backend release-unit 安全部署；不需要在 preheat-bundle 响应里维护双字段名增加 backend 复杂度。

---

## 7. 验收清单

| ID | 验收点 |
|---|---|
| F1 | `pnpm db:push` 成功，Prisma client 含 NovelDreamArtifact |
| F2 | Migration #1 跑完后 `SELECT COUNT(*) FROM "NovelDreamArtifact"` 等于 `Novel` 表行数中 characterBible 或 assetMapping 非空的行数 |
| F3 | §5.3 的一致性 SQL 在 Step 2 完成后返回 0 行 |
| F4 | `GET /api/internal/novels/:id/character-arcs` 返回 `{ novelId, characterArcs }`（旧路径 404） |
| F5 | `POST /api/admin/novels/:id/character-arcs/regenerate` 成功触发 preheat，写入 NovelDreamArtifact，响应含 `characterArcs` |
| F6 | `POST /api/internal/preheat-bundle/:id` 响应 body 含 `characterArcs`（不再含 `characterBible`） |
| F7 | dream-agent 容器跑 planner / writer / arc-review 任务，能正确消费 `character_arcs_json`（兼容期结束后旧 `character_bible_json` 引用全部清除） |
| F8 | `pnpm smoke:all` 全绿（含 dream-preheat-bundle-smoke / dream-triggers-e2e / v3-acceptance-check） |
| F9 | `pnpm lint` / `pnpm tsc` / `pnpm build` 全绿 |
| F10 | DATA-MODEL.md / 相关 spec 文档更新，wiki 同步入库 |

---

## 8. 不在本 spec 范围

- **不拆 NovelCharacter**：理由见 §0；如未来 chat 模块独立扩展再开 spec
- **不动 NovelCharacter 命名**：理由同上
- **不引入 characterArcs 历史版本表**：当前 admin 重生覆盖语义不变；如未来需要 A/B 对比再开 spec
- **不把 assetMapping 改名为 dreamAssetMapping**：名字本身准确，无歧义
- **不把 dreamEnabled 搬到 NovelDreamArtifact**：理由见 §0

---

## 9. 待执行 plan

本 spec 通过后，调用 `superpowers:writing-plans` 产出实施 plan：分 Step 1 / Step 2（按 §4.1 顺序拆 atomic commits）/ Step 3 三大阶段，每阶段独立 verifiable。
