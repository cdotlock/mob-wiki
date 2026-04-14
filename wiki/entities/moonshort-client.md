---
title: Moonshort Client
tags: [cocos, game, typescript, testing]
sources: [raw/2026-04-14-moonshort-client-skill.md, raw/2026-04-14-mobai-agent-memory.md]
created: 2026-04-14
updated: 2026-04-14
---

Cocos Creator 3.8.8 game frontend for Moonshort interactive fiction. Features a three-layer architecture (AppCore / EventBus / AppRenderer) that enables fully headless testing without the Cocos engine.

## Architecture

- **AppCore** — Pure logic state machine, zero Cocos dependencies
- **EventBus** — Generic pub/sub, typed events
- **AppRenderer** — Cocos UI layer, subscribes to bus events

## 16 Phases (State Machine)

**Auth:** login, inviteCode
**Main UI:** home, person, overview, addPoint, mall
**Minigame Loop:** minigameIntro, minigamePlaying, minigameResult
**Plot Loop:** plotPreVideo, plotSelection, plotCheck, plotPostVideo
**Terminal:** complete, death

## Headless Testing

`test/` directory runs without Cocos via `cc-mock.ts`:

- **play.ts** — AutoPlayer CLI: `BASE_URL=http://localhost:3000 MAX_ROUNDS=2 npx tsx play.ts`
- **run-tests.ts** — Test suite: AppCore, PhaseRegistry, Scenarios, UIEvents
- **TestRunner.ts** — Minimal home-built framework (no Jest/Mocha)

## API Client

Fetch-based HTTP client (`assets/api/ApiClient.ts`) with auto-token injection. Modules: AuthApi, NovelsApi, SavesApi, GameApi, MallApi, InventoryApi.

## Related

- [[entities/moonshort-backend]]
- [[entities/mobai-agent]]
- [[concepts/cli-gateway-protocol]]

## Sources

- [Client skill](../raw/2026-04-14-moonshort-client-skill.md)
