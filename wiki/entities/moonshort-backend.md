---
title: Moonshort Backend
tags: [nextjs, game-engine, prisma, postgresql, stripe, interactive-fiction]
sources: [raw/2026-04-14-mobai-agent-memory.md, raw/2026-04-14-cli-gateway-server-layer-design.md, docs/superpowers/specs/2026-04-24-remix-anywhere-design.md]
created: 2026-04-14
updated: 2026-05-03
---

Next.js full-stack application serving as the game engine, story delivery platform, admin dashboard, Remix runtime, and Dreaming Universe backend for Moonshort interactive fiction games. Handles player state management, story node delivery from upstream, D20 dice combat, economy systems, survival mechanics, minigames, achievements, payments via Stripe, remix/branching via LLM, Dream production/recommendation plumbing, and NPC character chat. The primary backend that [[entities/moonshort-client]] connects to for all gameplay operations.

## Tech Stack

- **Framework:** Next.js 16 (App Router + custom server.ts)
- **Database:** PostgreSQL via Prisma ORM v6.6.0
- **Authentication:** NextAuth v5 (Google OAuth + email/password)
- **Payments:** Stripe (checkout, webhooks, subscription management)
- **LLM Integration:** OpenAI-compatible (remix story generation, character chat)
- **Observability:** Langfuse (LLM call tracing)
- **CLI Framework:** Commander 12
- **Repository:** github.com/Rydia-China/noval.demo.2
- **Location:** `/Users/Clock/moonshort backend/backend/`
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
| `POST` | `/api/internal/compile-mss` | Writer specialist | Compile MSS source into EpisodeJSON and content hash without writing DB. |
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

The current implementation has an important limitation: the Python controller keeps many artifacts in memory (`planner_output_json`, `writer_drafts_json`, `reviewer_reports_json`, `mss_files`) and the backend `/progress` endpoint only persists selected fields. This means job inspection is improving, but durable checkpoint persistence is not yet complete.

### Character Chat Routes (`/api/character-chat/*` and `/api/ccr/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/character-chat/send` | Send a message to an NPC character. Uses LLM with the character's personality card as context. |
| `GET` | `/api/character-chat/sessions` | List character chat sessions |
| `GET` | `/api/character-chat/sessions/:id` | Get a specific chat session with message history |
| `GET` | `/api/character-chat/messages/:sessionId` | Get all messages for a chat session |
| `POST` | `/api/ccr/remix-persona` | Create a remixed version of a character's personality for alternative chat experiences |

### Admin Routes (`/api/admin/*`)

| Method | Path | Description |
|--------|------|-------------|
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

### User

User accounts with authentication. Fields: id, email, name, password (hashed), provider (local/google), role (user/admin), stripeCustomerId, subscriptionStatus, createdAt, updatedAt.

### Novel

Story container. Fields: id, title, description, coverImage, episodeCount, branchCount, status (draft/published), upstreamId (reference to content management system), createdAt, updatedAt.

### NovelNode

Individual story node in the narrative graph. Fields: id, novelId, nodeType (plot/decision/check/minigame/ending), parentId, branchId, episodeNumber, content (JSON with narrative text, media references, game mechanics), metadata (difficulty class, stat requirements, rewards), ordering, createdAt.

### CharacterCard

NPC character definitions for character chat. Fields: id, novelId, name, description, personality (LLM prompt defining the character's voice and behavior), avatar, traits (array of personality descriptors), createdAt.

### PlayerState

Player save file. Fields: id, userId, novelId, currentNodeId, episodeProgress, stats (combat/intelligence/charisma/will), hp, san, coins, gems, xp, level, inventory (JSON array of items), achievements (JSON array of earned achievement IDs), choices (JSON log of all decisions made), createdAt, updatedAt, isAlive.

### RemixSession

LLM-generated story branches. Fields: id, playerId, novelId, branchNodeId (where the branch diverges from the main story), prompt (user's remix request), generatedContent (LLM output), status (generating/published/draft), publishedAt.

### StoryBranch

Named story branches within a novel. Fields: id, novelId, name, description, parentBranchId, isMainline, createdAt.

### ChatSession

Character chat conversation. Fields: id, playerId, characterId, messages (JSON array), tokenCount, createdAt, lastActiveAt.

### Achievement

Earned achievement record. Fields: id, playerId, achievementTypeId, achievementType (1/2/3), earnedAt, metadata (JSON with specifics).

### Payment

Stripe payment records. Fields: id, userId, stripeSessionId, amount, currency, status (pending/completed/refunded), productType (gems/subscription), createdAt.

## Upstream Integration

The backend syncs novel content from an upstream content management system at `http://47.98.225.71:38188/api/internal/read`. Authentication uses a Bearer token. The sync process fetches novel metadata, story nodes, and character data, then upserts them into the local PostgreSQL database. The `noval sync` CLI command triggers this process.

## Related

- [[entities/mobai-agent]] -- Orchestrator agent that manages backend operations via CLI
- [[entities/moonshort-client]] -- Cocos game frontend that connects to this backend
- [[entities/dramatizer]] -- Upstream pipeline that produces story trees imported by this backend
- [[entities/cli-gateway]] -- CLI gateway for remote noval CLI execution
- [[concepts/cli-gateway-protocol]] -- HTTP API specification

## Sources

- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
- [CLI Gateway design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
