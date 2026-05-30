---
title: Dreaming Universe
tags: [dreaming, remix, recommendation, agent]
sources: []
created: 2026-05-03
updated: 2026-05-30
---

Dreaming Universe is Moonshort's product and technical system for turning a player's accumulated remix and play signals into complete playable hidden episode branches, then recommending those branches to similar players as signed "Dream" content. It sits above [[concepts/remix-anywhere]]: Remix Anywhere handles immediate local intervention, while Dreaming Universe turns long-term player taste into reusable shared narrative assets.

## Product Definition

Dreaming Universe is a shared generative branch universe. A high-signal player can become a producer without knowing the trigger threshold. The system uses that player's remix history, choices, relationship preferences, and novel context to generate a playable branch called a Dream. That Dream is then assigned to the producer and to other players whose taste profile matches it.

The product rule is:

| Dimension | Rule |
|---|---|
| Content | Visible and signed. Players can see that an entry is a Dream and who inspired it. |
| Algorithm | Hidden. Trigger thresholds, matching weights, cooldowns, and ranking are intentionally not exposed. |
| Experience | Dream branches must play like normal Moonshort episodes, not like detached prose summaries. |
| Ownership | Producer identity is a product surface. The system should preserve credit and long-tail recognition. |
| Recursion | Players can start Remix Anywhere inside Dream content, feeding future taste and hotness signals. |

The intended emotional moment is not "AI generated something"; it is "this branch understands my taste, and it came from another player I can recognize."

## Core Concepts

| Concept | Meaning |
|---|---|
| Dream | A complete playable hidden branch graph under the same novel. In storage it is standard episode JSON/MSS output, not a special runtime format. |
| Producer | A player whose accumulated behavior triggers Dream production. Producer rules are black-box. |
| Consumer | A player who receives an assigned Dream through recommendation. Most players are consumers. |
| Universe library | The shared pool of live/probation Dreams, including future official seeded Dreams if needed. |
| Taste coordinate | The internal profile vector or heuristic signature used to match producers, consumers, and Dreams. |
| Entry patch | A controlled overlay on a source episode that exposes the Dream entry when a session has an assignment. |
| Assignment | A session-specific record saying which Dream may appear at which source episode and slot. |

## Relationship To Remix Anywhere

Remix Anywhere and Dreaming Universe are stacked, not competing systems.

| Property | Remix Anywhere | Dreaming Universe |
|---|---|---|
| Time scale | Seconds to minutes | Hours to days |
| Input | One player intent at a current step | Accumulated player behavior plus full source context |
| Output | `InsertPatch` in the current episode plus forward callbacks | Hidden episode branch graph with signed entry |
| Visibility | Immediate, mostly personal | Shared, signed, recommended |
| Primary reward | "I changed this moment" | "The story understands my long-term taste" |
| Technical anchor | Stable step IDs and session patches | Episode graph plus assignment-gated entry overlay |

The Dreaming trigger chain can include Remix events. A player performs remixes, some succeed, some fail, forward callbacks fire, and the aggregate profile eventually becomes strong enough for the Dream producer trigger to enqueue a production job.

## Technical Model

The final technical direction is "large content is Episode, small entrance is Overlay."

Dream body content is stored as normal `Episode` rows:

```text
Episode.branchKey = "dream/<dreamId>"
Episode.episodeId = "dream/<dreamId>:01"
Episode.episodeId = "dream/<dreamId>:02"
```

The runtime does not need a special Dream walker. Once the player enters a Dream episode, the existing episode loader, step walker, choice evaluation, gate resolver, achievement logic, state effects, and Remix compatibility rules apply.

## Data Model

The Dream service data model lives in `services/dream/prisma/schema.prisma`, separate from the app's main Prisma schema.

| Table | Responsibility |
|---|---|
| `Dream` | Metadata for a generated branch: `novelId`, `branchKey`, `entryEpisodeId`, `episodeIds`, `entryPatch`, producer snapshot, profile snapshot, status, title, summary, hotness counters. |
| `DreamAssignment` | Session-level routing: `dreamId`, `sessionId`, `userId`, `novelId`, `sourceEpisodeId`, `entrySlotKey`, priority, score, reason, and lifecycle status. |
| `DreamEvent` | Event log for interactions such as assignment, visible entry, entry, completion, skip, remix within Dream, or collection. |
| `UserNovelProfile` | Aggregated user-novel behavior used by producer trigger and recommendation. |
| `DreamProductionJob` | Production job checkpoint table for the agent pipeline. |
| `DreamPreheatCache` | Cached source-context bundle metadata; bundle JSON lives in OSS. |

The app main schema still owns player-facing `Episode`, `Novel`, `PlayerSession`, and save state. The Dream service owns production and recommendation metadata. This separation is intentional because Dream production is expected to move toward a separate service boundary.

## Entry Patch

`Dream.entryPatch` is not MSS and is not compiled by the MSS compiler. It is a JSON list of controlled operations stored as `DreamEntryOperation[]`.

**2026-05-26 cutover**：3 个 v1 ops (`choice_add_option` / `choice_replace_option` / `replace_gate`) 全部 disable，只允许单一新 op **`bonus_only`**。详见 [[concepts/dream-bonus-only-op]]。

| 当前唯一允许的 op | 形状 | 行为 |
|---|---|---|
| `bonus_only` | `{ op, optionFlavor }`（只两字段；`optionFlavor` 是 LLM 出力的 ≤120 字钩子） | applier 在 source EP N 末尾追加合成 choice：Option A `Continue` (i18n template) → 原 `gate.next`；Option B `<optionFlavor>` → `dream/<dreamId>:01` |

旧 ops 在 `DreamEntryOperationSchema` 里仍能 parse（read back-compat），但 `WritableDreamEntryOperationSchema` 拒任何非 `bonus_only` 的 write。生产 + admin-inject 都过 writable 闸；read path（`dream-readonly-service` / presence overlay）仍 parse-tolerant。Legacy dream 由一次性 `scripts/cleanup-legacy-dream-ops.ts` 清。

entry patch 不是 top-level MSS fragment。MSS top level 只支持正常 `@episode`，把 `@replace_suffix` 之类硬塞 Go compiler 是结构性 bug。entry patch 由 backend overlay tooling 以 JSON 验证、预览、应用。

### autoAssign

`Dream.entryPatch.autoAssign: true` 让 dream 在 `createSession` post-commit 阶段被 `app/services/dream-autoassign-service.ts` 自动挂载（`(sessionId, dreamId)` 幂等，best-effort 不阻塞 session 创建）。是 mini Phase-4 recommender 兜底，给 demo / 强制教学 dream 用（见 [[concepts/villain-season-demo]]）。

### Feed Skip-to-E1

home feed 点 dream 卡进游戏，`createReplaySession` 看 `entryPatch` 第一条 op：

- `bonus_only` → 直接落 `dream.episodeIds[0]`（dream E1）
- legacy → 走旧 `entryEpisodeId`（source 集）+ player 端 auto-pick

auto-pick effect (`app/(player)/play/[sessionId]/page.tsx`) 和 `dream-source-detection` helper 保留作 legacy 兜底，不删。

## Dream Production Architecture

The 2026-05-01 real-agent rearchitecture split production into three layers:

| Layer | Implementation | Responsibility |
|---|---|---|
| Preheat workflow | Backend Node.js deterministic workflow | Build source context digests, rollups, and cacheable source bundles. |
| Agent layer | Python `services/dream-agent/` | Produce plan, MSS episodes, entry patch, and arc review through multi-agent tool use. |
| Backend gateway | Next.js internal APIs | Enforce database and episode write boundaries, compile MSS, preview overlays, and persist job progress. |

The Python service uses FastAPI and defaults to port `8765`. Backend workers call it through `POST /jobs/run`. Runtime prompts are meant to be pulled from Langfuse, while repository prompt files are upload sources.

## Dream-Agent Current State

As of 2026-05-02, the actual current implementation is a Python service using `smolagents.ToolCallingAgent`, not the earlier CodeAgent-only draft. The current topology is:

```text
backend outbox/BullMQ
  -> app/upstream/dream-agent-client.ts
  -> POST /jobs/run
  -> FastAPI dream-agent
  -> JobRunner
  -> DreamManagerAgent
  -> planner / writer / entry-patch / arc-review specialist tools
  -> backend internal APIs
```

The service has these important boundaries:

| Boundary | Current rule |
|---|---|
| Manager | Must call specialist tools. It must not directly author final plan, MSS, entry operations, or arc review. |
| Specialists | Produce narrow artifacts and save them into the controller checkpoint. |
| Controller | Owns in-memory checkpoint, retry budget, hard gate stubs, and terminal markers. |
| Backend | Is the only component allowed to write production episode rows and durable Dream service state. |
| Persistence gap | Not all Python in-memory checkpoint fields are written back to DB yet; progress endpoint only accepts selected fields. |

Current `/jobs/run` responses include `done`, `failed`, `in_flight`, `agent_loop_done`, and `agent_loop_failed`. The backend-side RPC timeout was extended because long LLM calls can exceed default HTTP client timeouts.

## Internal APIs

The Python dream-agent currently calls backend endpoints through `BackendClient`.

| Endpoint | Purpose |
|---|---|
| `GET /api/internal/dream-production-jobs/:jobId` | Fetch job snapshot: identity, status, stage, checkpoint, profile snapshot. |
| `POST /api/internal/dream-production-jobs/:jobId/progress` | Heartbeat and selected progress persistence. |
| `GET /api/internal/user-novel-profiles/:userId/:novelId` | Planner tool reads the producer's aggregate profile. |
| `GET /api/internal/novels/:novelId/episodes` | List source episodes; used by preheat and available to Python tooling. |
| `GET /api/internal/novels/:novelId/episodes/:episodeId/source` | Read compiled source episode packet for planning and entry patch work. |
| `POST /api/internal/preview-overlay-apply` | Validate and preview entry patch operations without writing DB. |
| `POST /api/internal/compile-mss` | Compile MSS to EpisodeJSON and content hash without writing DB or OSS. |
| `POST /api/internal/preheat-bundle/:novelId` | Build or fetch a preheat source bundle. |

Auth uses bearer tokens. Backend to dream-agent uses `DREAM_AGENT_BEARER`; dream-agent to backend uses `BACKEND_INTERNAL_BEARER`, which in dev maps to the backend cheat token.

## Job Lifecycle

The intended lifecycle is:

1. A producer event or Dream trigger creates a `DreamProductionJob` with `status = queued`.
2. Backend writes outbox topic `dream.production.agent-loop`.
3. BullMQ worker requires `DREAM_PRODUCTION_BACKEND=python`.
4. Worker best-effort marks the job `productionBackend = "python"`.
5. Worker calls `POST /jobs/run` with `{ "job_id": "...", "attempt": 1 }`.
6. Python JobRunner fetches the job snapshot and checks idempotency.
7. Manager calls specialists until plan, writer drafts, entry patch, and arc review exist.
8. Backend hard gates compile MSS and preview overlays.
9. Backend persists episodes and Dream metadata.
10. Assignment/recommendation makes the Dream visible to qualified sessions.

The current implementation is not yet fully DB-leased. If a job remains `queued`, repeated RPC can still re-enter the pipeline. Long timeouts and outbox dedupe reduce risk, but the durable lease/status transition is a known follow-up.

## Source Context Preheat

Preheat exists because a full novel can exceed direct agent context. The workflow produces source digests and rollups based on:

| Input dimension | Use |
|---|---|
| Total source character count | Decide batch size and rollup depth. |
| Episode count | Decide group rollups and hierarchical rollups. |
| Longest episode | Avoid splitting an episode in the middle. |
| Prompt version | Cache key must change when digest prompt changes. |
| Model config | Cache key must change when provider/model/temperature changes. |
| Source content hash | Cache key must change when compiled episode JSON changes. |

`DreamPreheatCache` stores metadata; the immutable bundle JSON is stored in OSS. This allows one source bundle to be reused across multiple producer jobs for the same novel and source version.

## Product Surfaces

Dreaming Universe should eventually expose:

| Surface | Player meaning |
|---|---|
| Dream entry label | Indicates this branch is Dream content, distinct from mainline or official PGC branch. |
| Producer byline | Shows which player profile inspired the Dream. |
| Producer self-entry | Producer can encounter their own Dream later and receive a special creator signal. |
| Collection | Completed Dreams enter a persistent collection/replay surface. |
| Hotness | Popular Dreams can display activity or weekly-hot markers. |
| Follow | Players may follow producers, lightly weighting future recommendations. |
| Notifications | Producers receive asynchronous recognition when their Dream is played. |

The app already has early player/admin surfaces in recent commits: player Dream entry cards, completion cards, Dream collection list, admin Dreams list/detail/debug pages, job detail checkpoints, and metrics rollup.

## Cross-References

- [[concepts/dream-bonus-only-op]] — 2026-05 起 entry-patch 唯一新 op + feed skip
- [[concepts/dream-trigger-v2-mechanical]] — producer 侧 dream 触发器 v2（mechanical evaluator）
- [[concepts/dream-rec-monorepo-migration]] — dream-rec 服务 subtree merge 进 backend monorepo
- [[concepts/novel-dream-artifact]] — `characterArcs` / `assetMapping` 1:1 sidecar 抽表
- [[concepts/villain-season-demo]] — 第一本 autoAssign + bonus_only 真用例
- [[concepts/remix-anywhere]] explains the immediate player intervention system that feeds long-term Dream signals.
- [[concepts/stable-step-id]] explains the content-addressed cursor system that makes entry overlays stable.
- [[entities/moonshort-backend]] owns the backend APIs, job queue, episode storage, and player path.
- [[entities/dramatizer-mss]] and [[entities/moonshort-script]] supply the MSS authoring and compilation concepts used by Dream writer specialists.

## Sources

This page was reconstructed from local repository history and files under `/Users/Clock/moonshort/backend`, especially:

- `docs/superpowers/specs/2026-04-28-dreaming-universe-product.md`
- `docs/superpowers/specs/2026-04-28-dreaming-design-v2.md`
- `docs/superpowers/specs/2026-05-01-dream-real-agent-rearchitecture.md`
- `services/dream-agent/README.md`
- `services/dream-agent/docs/architecture.md`
- Git history on branch `dreaming-universe` through 2026-05-02
