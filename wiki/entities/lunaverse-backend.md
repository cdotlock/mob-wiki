---
title: Lunaverse Backend
tags: [nextjs, game-engine, prisma, postgresql, supabase, r2, stripe, interactive-fiction]
sources: [raw/2026-04-14-mobai-agent-memory.md, raw/2026-04-14-cli-gateway-server-layer-design.md, docs/superpowers/specs/2026-04-24-remix-anywhere-design.md, raw/2026-05-30-backend-production-pipeline-two-phase.md]
created: 2026-04-14
updated: 2026-06-06
---

Next.js full-stack application serving as the game engine, story delivery platform, admin dashboard, Remix runtime, Dreaming Universe backend, and content release controller for Lunaverse interactive fiction games. Handles player state management, story node delivery from upstream, D20 dice combat, economy systems, survival mechanics, minigames, achievements, payments via Stripe, remix/branching via LLM, Dream production/recommendation plumbing, and NPC character chat. The primary backend that [[entities/lunaverse-client]] connects to for all gameplay operations.

## 2026-05/06 Major Refactors（要点速查）

| 改 | 摘要 | 详细 |
|---|---|---|
| **LS realignment 上线（2026-06-06）** | 新 LS 契约的 consumer cutover 落 prod：删 influence / goto / label / CG sub-steps / 3-slot stage / `Session.resolvedInfluences`，single-sprite stage；零删库（additive-only，prod schema 已是 HEAD 超集）；同批带 soul dark-launch + TLWB co-op + second-chorus Sera + recommended 端点 | [[concepts/ls-spec-redesign-2026-06]] · 部署机制 [[concepts/railway-production-deploy]] |
| **两阶段发布流程** | IDE submit → admin activate；`Novel.activeReleaseId` 是唯一真相；`NovelDraftAsset` / `Novel.status` / `NovelCharacter.voiceId` / `characterBible` 全删 | [[concepts/production-pipeline-two-phase]] |
| **Dream `bonus_only` op** | 3 个旧 entry-patch ops 全废，换成单一 terminal `bonus_only`；feed 入口直接落 dream E1 | [[concepts/dream-bonus-only-op]] |
| **Supabase 切换** | 生产 Postgres 从自管切到 Supabase；新库走专用 fresh-bootstrap，**不能** `migrate deploy` 从空库 replay | [[concepts/supabase-backend-bootstrap]] |
| **Cloudflare R2 主存储** | Aliyun OSS 兼容层完全摘掉；asset / TTS / episode JSON 全部走 R2 | 见下 §Storage |
| **mob-ai LiteLLM gateway 统一** | DeepSeek / Claude / GPT / Jina / image / video 全走 `https://ai.mob-ai.cn/api/v1`，单一 `MOB_AI_API_KEY`；slot→model mapping 三处镜像由 `pnpm lint:llm-registry` 强制一致 | [[entities/mob-ai-router]] |
| **Drama Remix 删除** | M7 整集再生成路径完全摘掉（service / 表 / route / client 全清），Remix Anywhere 是唯一玩家介入系统 | [[concepts/remix-anywhere]] |
| **Forward planner 整本化** | 旧 3-batch 流水线换成单 plan、2-stage pick→write 跨非 dream 全分支 | [[concepts/remix-anywhere]] |
| **Villain-Season demo** | 双语 EN+ZH 全机制 demo + 强制 dream + 英文 Breeze 配音 | [[concepts/villain-season-demo]] |

## Tech Stack

- **Framework:** Next.js 16 (App Router + custom server.ts)
- **Database:** PostgreSQL via Prisma ORM v6.6.0；生产托管在 **Supabase**（Railway 上 app/worker/tts/dream/dream-rec 5 个 service 全指向同一个 hosted DB），见 [[concepts/supabase-backend-bootstrap]]
- **Storage:** **Cloudflare R2**（所有 asset / TTS 音频 / episode JSON 唯一 storage backend；Aliyun 兼容层 2026-05 完全摘除）
- **Authentication:** 自家 JWT via `jose`（`app/lib/jwt-auth.ts`）；Supabase OAuth 作为 OAuth provider 但 backend 自签 JWT（[`docs/specs/supabase-auth.md`](https://github.com/cdotlock/lunaverse-backend/blob/main/docs/specs/supabase-auth.md)）；admin 走 HMAC cookie `noval_admin`（`requireAdmin`）；**项目不依赖 next-auth**
- **Payments:** Stripe (checkout, webhooks, subscription management)
- **LLM Integration:** mob-ai LiteLLM gateway (`https://ai.mob-ai.cn/api/v1`) — influence-judge / Jina embeddings + rerank / dream-agent specialists / dream-rec tagger 全部通过 `MOB_AI_API_KEY` 鉴权
- **Observability:** Langfuse (LLM call tracing via OpenTelemetry, 初始化在 `instrumentation.ts`)
- **CLI Framework:** Commander 12
- **Repository:** [github.com/cdotlock/lunaverse-backend](https://github.com/cdotlock/lunaverse-backend)
- **Location:** `/Users/Clock/lunaverse/backend/`
- **Port:** 3000

## Custom Server

The backend uses a custom `server.ts` that wraps the Next.js handler with a native Node.js HTTP server. This enables WebSocket support and custom middleware that the standard Next.js server does not provide. The custom server intercepts requests before passing them to the Next.js handler.

## API Surface (85+ Routes)

All API responses follow the envelope format:
```json
{
  "success": true,
  "data": { ... },
  "error": { "code": "ERROR_CODE", "message": "Human-readable message" }
}
```

### Player Routes (`/api/players/*`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/players` | List all player saves for the authenticated user |
| `GET` | `/api/players/:id` | Get a specific player save with full state |
| `POST` | `/api/players` | Create a new player save for a novel |
| `DELETE` | `/api/players/:id` | Delete a player save |
| `POST` | `/api/players/:id/actions` | Execute a game action (enterPlot, completePlot, selectChoice, diceRoll, completeMiniGame, useItem, etc.) |
| `GET` | `/api/players/:id/branches` | List available story branches for the current position |
| `GET` | `/api/players/:id/narratives` | Get the narrative content for the current story node |
| `POST` | `/api/players/:id/revive` | Revive a dead player (costs gems) |
| `POST` | `/api/players/:id/chat` | Send a message in the player's current context (for in-game chat features) |

### Novel Routes (`/api/novels/*`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/novels` | List all published novels available for play |
| `GET` | `/api/novels/:id` | Get novel details (title, description, cover, episode count) |
| `GET` | `/api/novels/:id/nodes` | Get story nodes for a novel (the narrative graph) |
| `GET` | `/api/novels/:id/nodes/:nodeId` | Get a specific story node with content |
| `POST` | `/api/novels/sync` | Trigger upstream sync from the content management system |

### Game Mechanic Routes (`/api/game/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/game/evaluate` | Evaluate a player choice against game rules. Processes dice checks, stat requirements, and economy costs. Returns the outcome with narrative text. |
| `POST` | `/api/game/reroll` | Re-roll a dice check (costs gems). The player can retry a failed check by spending premium currency. |
| `GET` | `/api/game/achievements` | List all achievements for the current player |
| `POST` | `/api/game/achievements/check` | Check if any new achievements have been earned based on current state |
| `GET` | `/api/game/achievements/types` | List all achievement type definitions |

### Remix Routes (`/api/remix/*`)

**Remix Anywhere system (2026-04-24, active)** — 详见 [[concepts/remix-anywhere]]

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/remix/submit` | 玩家长按对白或点角色立绘后提交 ≤50 字意图。Prescreen LLM 判 OOC + 选属性 + 发 DC；服务器预投骰决定胜负 |
| `POST` | `/api/remix/commit` | 玩家确认后 finalize remix；短轮询 sync2 LLM 产出的 `InsertPatch`，扣 20 gems 并写入 `SessionPatch`；失败则 `failedRemixPoints` 永久锁定 |
| `POST` | `/api/remix/drain-forward-plans` | 兜底：redispatch 卡住的 forward-plan 任务（玩家态限 remixId 范围，admin 态全局 drain） |
| `GET`  | `/api/remix/session-patches` | `?sessionId&episodeId` → 该玩家该集累积的 `InsertPatch[]` |
| `GET`  | `/api/remix/forward-plan-status` | `?remixId` → 3 个 forward-plan 任务的状态（queued/running/completed/failed） |

**Legacy Drama Remix 相关端点**（M7 时期，冻结特性开发，仅 bug 修复）涉及
`app/api/sessions/:id/drama-remixes/*` 下的整集生成工作流，走 dramatizer 上游。Drama Remix 和 Remix Anywhere 数据层互不干扰（outbox topic 命名空间分离：`drama-remix.*` / `assets-remix.*` vs `remix.sync2` / `remix.forward_plan`），但新功能应全部走 Remix Anywhere。

### Dreaming Universe Routes and Services

**Dreaming Universe system (2026-05-02, active development)** — 详见 [[concepts/dreaming-universe]].

Dreaming Universe turns accumulated player remix and play signals into complete hidden episode branches called Dreams. The backend owns player-path safety, episode storage, queue dispatch, internal APIs, admin inspection, metrics, and the TypeScript client that calls the Python `dream-agent` service. The system deliberately keeps generated Dream bodies as normal `Episode` rows and exposes them through assignment-gated source episode overlays.

Current backend components:

| Component | Path | Responsibility |
|---|---|---|
| Dream service DB schema | `services/dream/prisma/schema.prisma` | Owns `Dream`, `DreamAssignment`, `DreamEvent`, `UserNovelProfile`, `DreamProductionJob`, and `DreamPreheatCache`. |
| Production repository | `services/dream/production/` | Reads and updates Dream production jobs, metrics, and job artifacts. |
| Queue dispatch | `app/services/queue-processor-service.ts` | Handles `dream.production.agent-loop`; requires `DREAM_PRODUCTION_BACKEND=python` after the Node agent retirement. |
| Python client | `app/upstream/dream-agent-client.ts` | Calls `POST /jobs/run` on `services/dream-agent`; uses a long-lived undici Agent so long LLM runs do not hit a 5-minute default abort. |
| Internal API client for agent | `services/dream-agent/src/dream_agent/backend_client.py` | Python-side client for backend internal endpoints. |
| Preheat workflow | `app/services/dream-preheat/` | Builds and caches source context bundles for large novels. |
| Player Dream UI | `app/(player)/play/[sessionId]/components/DreamEntryCard.tsx`, `DreamCompletionCard.tsx`, `DreamBadge.tsx` | Shows Dream entry/completion surfaces inside gameplay. |
| Collection UI | `app/(player)/me/dreams/page.tsx` | Shows a player's Dream collection. |
| Admin UI | `app/admin/dreams/*` | Lists jobs, shows job details/checkpoints, debug tools, manual production forms, and metrics. |

Internal Dream APIs:

| Method | Path | Caller | Description |
|---|---|---|---|
| `GET` | `/api/internal/dream-production-jobs/:jobId` | Python `JobRunner` | Fetch DreamProductionJob identity, status, stage, checkpoint fields, and profile snapshot. |
| `POST` | `/api/internal/dream-production-jobs/:jobId/progress` | Python heartbeat/finalizer | Update `stage` and selected JSON artifacts such as manager decisions, entry patch, and hard-gate reports. |
| `GET` | `/api/internal/user-novel-profiles/:userId/:novelId` | Planner specialist | Read `UserNovelProfile` plus latest producer profile snapshot. |
| `GET` | `/api/internal/novels/:novelId/episodes` | Preheat / agent tools | List source episodes, excluding Dream branches. |
| `GET` | `/api/internal/novels/:novelId/episodes/:episodeId/source` | Planner and entry-patch tools | Read compiled source episode JSON and metadata. |
| `POST` | `/api/internal/preview-overlay-apply` | Entry-patch specialist | Apply `DreamEntryOperation[]` in memory and report applied/skipped operations. |
| `POST` | `/api/internal/compile-ls` | Writer specialist | Compile LS source into EpisodeJSON and content hash without writing DB. |
| `POST` | `/api/internal/preheat-bundle/:novelId` | Preheat client | Build or fetch cached source context bundle. |

Python `dream-agent` integration:

| Variable | Side | Purpose |
|---|---|---|
| `DREAM_PRODUCTION_BACKEND=python` | backend | Forces BullMQ Dream production jobs to use the Python service; the old Node in-process agent was retired. |
| `DREAM_AGENT_URL` | backend | Base URL for the FastAPI service, default `http://localhost:8765`. |
| `DREAM_AGENT_BEARER` | backend + Python | Bearer token for backend -> dream-agent calls. |
| `DREAM_AGENT_RPC_TIMEOUT_MS` | backend | Long RPC timeout; default was raised for multi-minute LLM runs. |
| `BACKEND_INTERNAL_URL` | Python | Backend base URL for internal APIs. |
| `BACKEND_INTERNAL_BEARER` | Python | Bearer token used by dream-agent -> backend calls; in dev it matches `CHEAT_TOKEN`. |

The current implementation has an important limitation: the Python controller keeps many artifacts in memory (`planner_output_json`, `writer_drafts_json`, `reviewer_reports_json`, `ls_files`) and the backend `/progress` endpoint only persists selected fields. This means job inspection is improving, but durable checkpoint persistence is not yet complete.

### Character Chat Routes (`/api/character-chat/*` and `/api/ccr/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/character-chat/send` | Send a message to an NPC character. Uses LLM with the character's personality card as context. |
| `GET` | `/api/character-chat/sessions` | List character chat sessions |
| `GET` | `/api/character-chat/sessions/:id` | Get a specific chat session with message history |
| `GET` | `/api/character-chat/messages/:sessionId` | Get all messages for a chat session |
| `POST` | `/api/ccr/remix-persona` | Create a remixed version of a character's personality for alternative chat experiences |

### Admin Routes (`/api/admin/*`)

Admin 走 HMAC cookie `noval_admin`（`requireAdmin`，`app/lib/admin-auth.ts`）。2026-05 C1 phase 把 admin 从单体列表扩成 per-novel 控制台。

**Production Release（新，IDE submit + admin 审核）** — 详见 [[concepts/production-pipeline-two-phase]]

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/admin/novels/:novelId/production/releases` | **IDE submit 入口**：写 L2 snapshot 成 `pending`；不动 L1 |
| `POST` | `/api/admin/novels/:novelId/production/releases/:releaseId/activate` | admin 把 `pending` / `superseded` → `live`，re-materialize L1 |
| `POST` | `/api/admin/novels/:novelId/production/releases/:releaseId/rollback` | 把 superseded release 切回 live（旧 live → superseded） |
| `POST` | `/api/admin/novels/:novelId/production/releases/:releaseId/reject` | `pending` → `failed`（body `{ reason }`，最长 2000 字） |
| `GET` | `/api/admin/novels/:novelId/production/releases/list` | 列 release + `activeReleaseId` |
| `GET` | `/api/admin/novels/:novelId/production/releases/:releaseId/diff?against=:otherId` | release 间 diff（默认 vs 当前 live） |
| `POST` | `/api/admin/novels/:novelId/characters/:slug/voice-profiles/:profileId/activate` | 切换某角色的 active voice profile |

**Novel / Character / Achievement（保留）**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/admin/novels` | List all novels (including unpublished) |
| `POST` | `/api/admin/novels` | Create a new novel entry |
| `PUT` | `/api/admin/novels/:id` | Update novel metadata |
| `DELETE` | `/api/admin/novels/:id` | Delete a novel |
| `GET` | `/api/admin/novels/:id/characters` | List characters for a novel |
| `POST` | `/api/admin/novels/:id/characters` | Add a character card |
| `PUT` | `/api/admin/characters/:id` | Update a character card |
| `DELETE` | `/api/admin/characters/:id` | Delete a character card |
| `GET` | `/api/admin/ach` | List achievement definitions |
| `POST` | `/api/admin/ach/login` | Admin authentication for the achievement system |
| `POST` | `/api/admin/ach/type1` | Create a Type 1 (milestone) achievement |
| `POST` | `/api/admin/ach/type2` | Create a Type 2 (story) achievement |
| `POST` | `/api/admin/ach/type3` | Create a Type 3 (collection) achievement |
| `GET` | `/api/admin/type2-stories` | List Type 2 story achievement configurations |
| `POST` | `/api/admin/type2-stories` | Create a Type 2 story achievement |

**Deprecated / Removed（2026-05）**

| Status | Endpoint | 替代 |
|---|---|---|
| **REMOVED** | 旧 draft-asset upload route | 全部入 `manifest.assets[]`，走 submit |
| **DEPRECATED** | `PATCH /api/admin/novels/:id/voices` | `manifest.voiceProfiles[]`；返 `X-Deprecated: true` / `Sunset: TBD` |
| **DEPRECATED** | `PATCH /api/admin/characters/:characterId/voice` | 同上；非 null `voiceId` 会被忽略 |

### Admin Console Pages（2026-05 C1）

per-novel 控制台落地后，原本平铺的 admin 列表升级成 novel dashboard 树形导航：

| 页面 | 路径 | 用途 |
|---|---|---|
| Dashboard | `/admin/dashboard` | 总览 + 待审 release 计数（`pending` 数量 badge） |
| Novel List | `/admin/novels` | 全 novel 列表，title 链到 per-novel dashboard |
| Per-Novel Dashboard | `/admin/novels/:id` | 单本入口：releases / characters / assets tile |
| Release Center | `/admin/novels/:id/releases` | 列所有 release（状态 + creator + activated by） |
| Release Detail | `/admin/novels/:id/releases/:releaseId` | diff + audit + asset list；activate / rollback / reject 按钮 |
| Asset Browser | `/admin/novels/:id/assets` | per-novel asset 按 kind 分组浏览 |
| Voice Profile Mgmt | `/admin/novels/:id/characters/:slug/voices` | 单角色多 voice profile + audition player + activate 按钮 |

UI building blocks：`ReleaseStatusBadge` / `ReleaseDiffCard`（asset 按 kind 分组）/ `AssetCard`（kind-aware 预览）/ `VoiceProfileCard`（audition player + activate）/ static `KindIcon`。所有新页面挂 admin cookie 闸（`f6101686`）。

### Payment Routes (`/api/stripe/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/stripe/checkout` | Create a Stripe checkout session for purchasing gems or subscriptions |
| `POST` | `/api/stripe/webhook` | Stripe webhook endpoint for payment confirmations, subscription updates, and refunds |
| `GET` | `/api/stripe/subscription` | Get the current user's subscription status |
| `POST` | `/api/stripe/portal` | Create a Stripe customer portal session for managing subscriptions |

### Authentication Routes (`/api/auth/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Email/password login |
| `POST` | `/api/auth/register` | Create a new account |
| `POST` | `/api/auth/logout` | End the session |
| `GET` | `/api/auth/me` | Get the current authenticated user |
| `GET` | `/api/auth/google` | Initiate Google OAuth flow |
| `GET` | `/api/auth/google/callback` | Google OAuth callback |

### Utility Routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/tts/synthesize` | Text-to-speech synthesis for narration |
| `GET` | `/api/health` | Health check endpoint |
| `GET` | `/api/mall` | Get the in-game store catalog (items, prices in coins/gems) |
| `GET` | `/api/notifications` | Get notifications for the current user |

## CLI: noval

Standalone TypeScript CLI at `cli/bin/noval.ts`, built with Commander 12. Provides command-line access to all game operations for testing, automation, and debugging.

### All 10 Commands

**`noval sync`** -- Synchronize novel data from the upstream content management system. Flags: `--novel <id>` (sync a specific novel instead of all), `--force` (overwrite local changes).

**`noval list`** -- List novels. Flags: `--remote` (list from upstream instead of local database), `--branches` (include branch information for each novel).

**`noval play <novelId>`** -- Interactive gameplay from the command line. This is the most feature-rich command. Flags:
- `--ep <number>` -- Start from a specific episode
- `--ep-end <number>` -- Stop after reaching this episode
- `--choice <indices>` -- Pre-select choices (comma-separated, e.g., "0,1,0,2")
- `--auto` -- Automatic mode (selects random choices)
- `--strategy <name>` -- Choice strategy for auto mode (random, first, last, smart)
- `--admin` -- Admin mode (bypasses restrictions)
- `--model <name>` -- LLM model override for remix/chat features
- `--base-url <url>` -- LLM API base URL override
- `--api-key <key>` -- LLM API key override
- `--media` -- Enable media playback (TTS, images)
- `--minigame` -- Enable minigame encounters
- `--minigame-score <number>` -- Override minigame score (for testing)
- `--dice <number>` -- Override dice roll result (for deterministic testing)
- `--coins <number>` -- Set starting coins
- `--gems <number>` -- Set starting gems
- `--verbose` -- Show detailed game state after each action
- `--json` -- Output structured JSON for automation

**`noval show <novelId>`** -- Display novel details including episode list, character count, and branch structure.

**`noval remix <novelId>`** -- Start a remix session. Creates an LLM-powered alternative story branch from a specified position.

**`noval chat <characterId>`** -- Start an interactive character chat session with an NPC.

**`noval topup <playerId>`** -- Add currency to a player save. Used for testing economy features.

**`noval import <file>`** -- Import a story tree JSON file (typically exported from [[entities/dramatizer]]). Creates or updates the novel and its nodes in the database.

**`noval config`** -- Show or edit CLI configuration (API endpoints, LLM settings, default flags).

**`noval test`** -- Run automated test scenarios against the backend API.

### CLI Configuration

The CLI uses a `CliConfig` object with the following sections:

```typescript
{
  llm: {
    model: string,        // LLM model name
    baseUrl: string,      // API endpoint
    apiKey: string,       // API key
  },
  upstream: {
    url: string,          // Upstream content API URL
    token: string,        // Bearer token for upstream
  },
  langfuse: {
    publicKey: string,
    secretKey: string,
    host: string,
  },
  toggles: {
    media: boolean,       // Enable media playback
    minigame: boolean,    // Enable minigames
    verbose: boolean,     // Verbose output
    json: boolean,        // JSON output mode
  },
  player: {
    coins: number,        // Default starting coins
    gems: number,         // Default starting gems
  }
}
```

## Game Systems

### D20 Dice System

Skill checks use a D20 (20-sided die) system. The player has four stats: combat, intelligence, charisma, and will. Each stat ranges from 1-20 and is set during character creation via the `addPoint` phase. When a story node requires a skill check, the game rolls a D20 and adds the relevant stat modifier. The result is compared against a difficulty class (DC) set by the story node. Success advances the story; failure may trigger damage, sanity loss, or branch to an alternative outcome.

### Economy System (Coins and Gems)

**Coins** -- Standard currency earned through gameplay (completing episodes, winning minigames, achievements). Used to purchase items in the mall, revive characters, and access special story branches.

**Gems** -- Premium currency purchased with real money via Stripe. Used for dice re-rolls, premium items, exclusive story branches, and character revives when coins are insufficient.

### Survival System (HP and SAN)

**HP (Health Points)** -- Tracks physical health. Reduced by combat encounters, traps, and bad choices. When HP reaches 0, the player enters the `death` phase. HP can be restored by items, rest events in the story, or reviving.

**SAN (Sanity)** -- Tracks mental health on a 0-100 scale. Reduced by horror encounters, disturbing revelations, and certain story events. Low sanity triggers altered narrative descriptions and may force the player into specific story branches. SAN is harder to restore than HP, typically requiring specific story events or premium items.

### Minigame System

Story nodes can trigger minigames -- short interactive challenges. Minigames produce a score that is mapped to a letter grade:

| Grade | Score Range | Reward Multiplier |
|-------|-------------|-------------------|
| S | 95-100 | 3x |
| A | 80-94 | 2x |
| B | 60-79 | 1.5x |
| C | 40-59 | 1x |
| D | 0-39 | 0.5x |

The grade affects the narrative outcome and rewards. Higher grades unlock better story branches and more coins. The minigame type and parameters are defined in the story node data.

### Achievement System

Three types of achievements:

**Type 1 (Milestone)** -- Triggered by reaching specific game milestones. Examples: complete a novel, reach episode 10, accumulate 1000 coins. Tracked by checking player state against predefined conditions.

**Type 2 (Story)** -- Tied to specific story events or choices. Examples: discover a secret ending, make a specific choice combination, trigger a hidden scene. Defined per-novel by content creators in the admin dashboard.

**Type 3 (Collection)** -- Awarded for collecting sets of items, characters, or experiences. Examples: encounter all characters in a novel, collect all items in the mall, complete all minigames with S grade.

### XP and Leveling

Players earn experience points (XP) through gameplay actions: completing episodes, winning minigame challenges, discovering achievements. XP accumulates toward level thresholds, with each level unlocking potential rewards or access to premium content.

## Data Model

> 2026-05 起 IDE 上游契约从 LS-only 升级成 Production Manifest（含 asset / voice / prompt 元信息）。Schema 大改：见 [[concepts/production-pipeline-two-phase]] §4 的字段表。下面只列**当前**字段；2026-05 已删字段单独标出。

### User

User accounts with authentication. Fields: id, email, username, passwordHash (CLI / smoke 仍用), salt, supabaseUserId (OAuth), googleEmail / googleName / googleAvatar (Supabase OAuth identity 写入), role (user/admin), stripeCustomerId, subscriptionStatus, createdAt, updatedAt.

### Novel

Story container. Fields: id, title, synopsis, coverUrl, coverVideo, coverVideoThumbnail, narratorVoiceId, mcVoiceId, language, **archived** (bool), **activeReleaseId** (FK → NovelProductionRelease), createdAt, updatedAt.

**已删 2026-05**：
- ~~`status` (draft/published)~~ → 替成 `archived` + `activeReleaseId`（"上线了" = `NOT archived AND activeReleaseId IS NOT NULL`）
- ~~`characterBible` (JSON)~~ → 抽到 `NovelDreamArtifact.characterArcs`（详见 [[concepts/novel-dream-artifact]]）
- ~~`assetMapping` (JSON)~~ → 同上，抽到 `NovelDreamArtifact`

### NovelProductionRelease（新，2026-05）

发布快照。Fields: id, novelId, status (`pending` / `live` / `superseded` / `failed`), releaseKey (per-novel unique), idempotencyKey (per-novel unique), manifestJson (Zod-validated), manifestHash, source ("ide"), ideVersion, createdAt, createdBy, activatedAt, activatedBy, supersededAt, failureReason. 状态机详见 [[concepts/production-pipeline-two-phase]] §Release-状态机。

### NovelAsset（新，2026-05）

L2 asset 行，bind 到 release。Fields: id, novelId, releaseId, localId, kind (`cover` / `character_image` / `bg` / `cg` / `music` / `sfx` / `episode_json` / `ls` / `tts_audition_audio`), name, ossKey, ossUrl, contentHash, mimeType, sizeBytes, source (`ide` / `generated` / `uploaded`), promptRunId, metadata. 替代了已删的 `NovelDraftAsset` 表。

### NovelDreamArtifact（新，2026-05-24）

1:1 sidecar of Novel，装 `characterArcs`（旧 `characterBible` 改名）+ `assetMapping` + 审计字段 `characterArcsMeta` / `assetMappingMeta`（promptVersion / generatedAt / sourceEpisodeHash）。详见 [[concepts/novel-dream-artifact]]。

### NovelCharacter

Fields: id, novelId, slug, displayName, role (`MC` / `lead` / `supporting` / `minor`), isProtagonist, avatarUrl, createdAt, updatedAt.

**已删 2026-05**：~~`voiceId`~~ → 替成 `CharacterVoiceProfile` 行；~~`portraits`~~ → 替成 `CharacterAsset` 行。

### CharacterVoiceProfile（新，2026-05）

Per-character 多语音 profile，唯一一行 `isActive=true`（partial unique index `idx_character_voice_profile_active` 强制）。Fields: id, characterId, provider (`breeze`), voiceId, generatedVoiceId, voiceDescription, auditionText, auditionAudioAssetId, promptRunId, savedAt, isActive. 玩家代码读语音走 `app/lib/get-active-voice.ts`。

### CharacterAsset

per-look 角色素材。Fields: id, characterId, assetId, look, usage (`portrait` / `sprite` / `fullbody`), isDefault.

### EpisodeAssetUsage

episode → asset 使用关系。Fields: id, episodeId, assetId, usageKind (`bg` / `character_show` / `cg` / `music` / `sfx`), stepId, characterSlug, look.

### PromptRun

Langfuse 元信息。Fields: id, releaseId, localId, provider (`langfuse`), promptName, promptVersion, traceId, purpose (`character_voice` / `image_prompt` / `bg_prompt` / `cg_prompt` / `music_prompt` / `sfx_prompt` / `asset_plan` / `episode_compile`), inputHash, outputHash, metadataJson.

### Episode

不可变 episode 行。Fields: id, novelId, episodeId, branchKey, seq, title, jsonUrl (R2), lsUrl (R2), contentHash, compiledAt.

### Session / Save

玩家存档。Fields: id, userId, novelId, currentEpisodeId, currentCursor (`(string|number)[]`), status (`Active` / `Completed` / `Dead` / `ToBeContinued`), `dreamReplayAssignmentId`, `failedRemixPoints` (`(episodeId, stepId)`), state JSONs.

### Dream / DreamAssignment / DreamEvent / UserNovelProfile / DreamProductionJob / DreamPreheatCache

详见 [[concepts/dreaming-universe]]。Schema 在 `services/dream/prisma/schema.prisma`（独立 Prisma client）。

### Remix / RemixForwardPlan / SessionPatch

详见 [[concepts/remix-anywhere]]。forward-plan 2026-05-24 从 3-batch 改单 plan + 2-stage pipeline。

### CharacterCard

NPC character definitions for character chat. Fields: id, novelId, name, description, personality (LLM prompt defining the character's voice and behavior), avatar, traits (array of personality descriptors), createdAt.

### ChatSession

Character chat conversation. Fields: id, playerId, characterId, messages (JSON array), tokenCount, createdAt, lastActiveAt.

### Achievement

Earned achievement record. Fields: id, playerId, achievementTypeId, achievementType (1/2/3), earnedAt, metadata (JSON with specifics). `AchievementUnlock (userId, achievementId)` unique；STORY / GLOBAL / REALTIME 三类共表，`kind` 字段区分。

### Payment

Stripe payment records. Fields: id, userId, stripeSessionId, amount, currency, status (pending/completed/refunded), productType (gems/subscription), createdAt.

### OutboxEvent

Append-only event log；BullMQ worker 消费 `remix.sync2` / `remix.forward_plan` / `dream.production.agent-loop` / `assets-remix.*` / `tts.*` 等 topic。

## Storage（Cloudflare R2，2026-05）

R2 是**唯一** storage backend（spec §10.5）。Aliyun OSS 兼容代码 2026-05 完全摘掉（`d0daba4f` refactor + `5e0df575` 完成 wiring + `a47e43db` 清 leftovers）。涉及 path：

- `app/lib/oss-service.ts` — 客户端
- `scripts/_seed-helpers/oss-client.ts` — seed 用
- `services/tts/` — TTS 音频直传 R2

`compiled.{en,zh}.json` 在 villain-season demo 中显式记 R2 URL。

历史 OSS 直读 cert 桥接（`scripts/with-system-ca.cjs` 自动注入 `NODE_EXTRA_CA_CERTS`）仍保留 — 旧 Aliyun cert chain 在 Node 22 内置 trust store 不全，但 R2 用 Cloudflare cert 没这个问题；桥接对 R2 无负担，可作通用安全网保留。

## LLM Gateway（mob-ai LiteLLM 统一）

所有 LLM 调用统一过 [[entities/mob-ai-router]]（`https://ai.mob-ai.cn/api/v1`，单一 `MOB_AI_API_KEY`）：

- influence-judge
- Jina embeddings + rerank
- dream-agent specialists（planner / writer / reviewer / entry-patch）
- dream-rec tagger

Slot → model mapping **三处镜像**，`pnpm lint:llm-registry` 强制三方一致：

| 镜像位置 | 用途 |
|---|---|
| `app/lib/llm/model-registry.ts` | TS source of truth |
| `services/dream-rec/app/config/llm_models.py` | dream-rec (Python) |
| `services/dream-agent/src/mob-ai.ts` | dream-agent (TS) |

切某 slot 的 model：改 `DEFAULTS[slot]` 三处 + 跑 `pnpm lint:llm-registry`（CI gate）；ad-hoc 用 `LLM_MODEL_PRO` / `LLM_MODEL_FAST` / `LLM_MODEL_TAGGER` / `EMBEDDING_MODEL` / `RERANKER_MODEL` env 覆盖。

## Upstream Integration

The backend syncs novel content from upstream via [[entities/lunaverse-ide]] submitting production manifests（[[concepts/production-pipeline-two-phase]]）。**已弃** legacy upstream 47.98.225.71 拉取路径（IDE 还自己跑分仓的旧 noval CLI 时用，现在 IDE 走 submit endpoint 直接 PUSH 内容）。

`noval sync` CLI 命令仍支持但仅作 dev 内部 debug。

## Related

- [[concepts/production-pipeline-two-phase]] — IDE submit + admin activate 流程
- [[concepts/dreaming-universe]] — Dream 系统父概念
- [[concepts/dream-bonus-only-op]] — 2026-05 dream entry-patch 唯一新 op
- [[concepts/remix-anywhere]] — 玩家长按介入 + forward planner
- [[concepts/villain-season-demo]] — 第一本走全两阶段流程的 demo
- [[concepts/supabase-backend-bootstrap]] — Supabase fresh-bootstrap 流程
- [[concepts/novel-dream-artifact]] — characterArcs / assetMapping 抽表
- [[concepts/dream-rec-monorepo-migration]] — dream-rec subtree merged 进 `services/dream-rec/`
- [[entities/mobai-agent]] — Orchestrator agent that manages backend operations via CLI
- [[entities/lunaverse-client]] — Cocos game frontend that connects to this backend
- [[entities/lunaverse-ide]] — Upstream IDE that submits production manifests
- [[entities/mob-ai-router]] — LLM gateway used for all calls
- [[entities/cli-gateway]] — CLI gateway for remote noval CLI execution
- [[concepts/cli-gateway-protocol]] — HTTP API specification

## Sources

- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
- [CLI Gateway design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
- [Production Pipeline Two-Phase mirror](../raw/2026-05-30-backend-production-pipeline-two-phase.md)
- [Dream bonus_only spec mirror](../raw/2026-05-30-dream-bonus-only-and-feed-skip-design.md)
- [Supabase DB runbook mirror](../raw/2026-05-30-production-manifest-supabase-db.md)
- [Villain-season README mirror](../raw/2026-05-30-villain-season-readme.md)
