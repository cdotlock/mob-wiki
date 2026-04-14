---
title: Moonshort Client
tags: [cocos, game, typescript, testing, state-machine, interactive-fiction]
sources: [raw/2026-04-14-moonshort-client-skill.md, raw/2026-04-14-mobai-agent-memory.md, raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

Cocos Creator 3.8.8 game frontend for Moonshort interactive fiction. Features a three-layer architecture (AppCore / EventBus / AppRenderer) that cleanly separates pure game logic from the rendering engine, enabling fully headless testing from Node.js without the Cocos runtime. Connects to [[entities/moonshort-backend]] for all game data and server-side logic.

## Tech Stack

- **Engine:** Cocos Creator 3.8.8
- **Language:** TypeScript
- **External Dependencies:** Zero (only firebase for analytics)
- **Test Runtime:** Node.js (via tsx) with minimal Cocos mocks
- **Location:** `/Users/Clock/moonshort backend/moonshort/`
- **Backend Connection:** `http://localhost:3000` (the [[entities/moonshort-backend]])

## Three-Layer Architecture

### AppCore (Pure Logic Layer)

The AppCore is a pure TypeScript state machine with zero Cocos Creator dependencies. It manages all game logic: phase transitions, data loading, action processing, and state queries. Because it has no dependency on any rendering framework, it can be instantiated and driven entirely from Node.js for testing.

The AppCore maintains two state domains:
- **Business State:** User data, novel catalog, game progress, stats, inventory, economy
- **Control State:** Current phase, navigation history, loading flags, error conditions

State mutations only happen through action processing. The AppCore receives action events from the EventBus, processes them against the current state and server responses, and emits notification events with the results.

### EventBus (Typed Pub/Sub Layer)

A generic typed publish-subscribe system that connects the AppCore and AppRenderer without either knowing about the other. All communication flows through the bus:

- **Action events** (prefix `action:`) -- Sent by the UI (or test harness) to request state changes
- **Notification events** (prefix `notify:`) -- Sent by the AppCore to announce state changes
- **Data events** -- Carry payload data for complex operations

The EventBus supports typed event definitions, ensuring compile-time safety for event names and payload types. When `DEBUG` is enabled, all events are logged to the console for debugging.

### AppRenderer (Cocos UI Layer)

The Cocos Creator rendering layer. Subscribes to EventBus notification events and updates the visual UI accordingly. Also captures user input (taps, swipes, button clicks) and emits action events onto the bus.

The AppRenderer is the only layer that depends on Cocos Creator APIs. It is entirely passive: it never directly mutates game state, and it never directly calls the AppCore. All interaction flows through the EventBus.

## All 16 Phases (State Machine)

The game operates as a state machine with 16 phases. Each phase defines what UI is displayed, what actions are valid, and what transitions are possible.

### Authentication Phases

**`login`** -- Initial phase. Shows login/registration UI. Valid actions: `action:quick-login` (auto-register with generated credentials), `action:login` (email/password login). Transitions to `inviteCode` if the account requires activation, otherwise to `home`.

**`inviteCode`** -- Shown when the account is not yet activated. Valid actions: `action:activate` (submit an invite code). Transitions to `home` on success.

### Main UI Phases

**`home`** -- Novel catalog view. Shows available novels with covers and descriptions. Valid actions: `action:select-novel` (choose a novel to play), `action:tab-switch` (switch between home and person tabs), `action:open-mall`, `action:logout`. Transitions to `overview` when a novel is selected.

**`person`** -- Player profile view. Shows stats, achievements, and settings. Valid actions: `action:tab-switch` (back to home), `action:open-mall`, `action:logout`. Reached via tab switch from `home`.

**`overview`** -- Novel detail view with save management. Shows novel description, episode progress, and save state. Valid actions: `action:start-novel` (create new save, shown when no save exists), `action:continue-novel` (resume existing save, shown when save exists), `action:back`. Transitions to `addPoint` for new games or to the appropriate plot phase for continued games.

**`addPoint`** -- Character stat allocation. The player distributes points across four stats: combat, intelligence, charisma, and will. Valid actions: `action:submit-points` (finalize stats with the four values). Transitions to the first plot phase after submission.

**`mall`** -- In-game store. Shows purchasable items with prices in coins or gems. Valid actions: `action:back` (return to previous phase), purchase actions for individual items. Can be opened from any phase via `action:open-mall`.

### Minigame Loop Phases

**`minigameIntro`** -- Shows minigame introduction and rules before play. Valid actions: `action:start-minigame`. Transitions to `minigamePlaying`.

**`minigamePlaying`** -- Active minigame gameplay. The specific minigame type and parameters are defined by the story node. Valid actions: `action:minigame-complete` (report the score and rating when the game ends). Transitions to `minigameResult`.

**`minigameResult`** -- Shows minigame results (score, grade, rewards). Valid actions: `action:confirm-result`. Transitions back to the plot loop.

### Plot Loop Phases

**`plotPreVideo`** -- Plays a pre-decision narrative video or animation. Valid actions: `action:video-end` (when the video finishes). Transitions to `plotSelection`.

**`plotSelection`** -- The core decision phase. Shows the current story node's narrative text and available choices. For branching nodes, displays multiple options. Valid actions: `action:select-plot-option` (choose an option by `decisionIndex` and `optionIndex`). Transitions to `plotCheck` if the choice requires a dice check, or to `plotPostVideo` if the choice is resolved immediately.

**`plotCheck`** -- Dice roll phase for stat checks. Shows the required stat, difficulty class, and current stat value. Valid actions: `action:dice-roll` (roll the D20). Transitions to `plotPostVideo` with the check result (success/failure).

**`plotPostVideo`** -- Plays a post-decision narrative video showing the outcome. Valid actions: `action:video-end`. Transitions to the next `plotPreVideo` (continuing the story), `minigameIntro` (if next node is a minigame), `complete` (if the story ends), or `death` (if HP reached 0).

### Terminal Phases

**`complete`** -- Story completion screen. Shows final stats, achievements earned, and rewards. Valid actions: `action:go-home` (return to novel catalog), `action:restart` (start a new playthrough).

**`death`** -- Player death screen. Shown when HP reaches 0. Valid actions: `action:go-home` (return to catalog), `action:revive` (revive the character, costs gems/coins).

### Phase State Machine Flow

```
login --> [inviteCode] --> home <--> person
                            |
                            v
                         overview --> addPoint
                            |
                            v
              plotPreVideo --> plotSelection --> plotCheck
                   ^              |                |
                   |              v                v
              plotPostVideo <-----+----------------+
                   |
                   v
              minigameIntro --> minigamePlaying --> minigameResult
                   |                                     |
                   +-------------------------------------+
                   |
                   v
              complete / death --> (restart/revive) --> home
```

## All EventBus Action Events

The complete table of action events that drive the game state machine:

| Action Event | Payload Type | Phase Context | Description |
|-------------|-------------|---------------|-------------|
| `action:quick-login` | `{}` | `login` | Auto-register with generated credentials and log in immediately |
| `action:login` | `{ username: string, password: string }` | `login` | Log in with email/password credentials |
| `action:activate` | `{ inviteCode: string }` | `inviteCode` | Submit an invite code to activate the account |
| `action:select-novel` | `{ novelId: string }` | `home` | Select a novel from the catalog to view its details |
| `action:tab-switch` | `{ target: 'home' \| 'person' }` | `home`, `person` | Switch between the home and person tabs |
| `action:start-novel` | `{}` | `overview` (no existing save) | Start a new playthrough, creating a fresh player save |
| `action:continue-novel` | `{}` | `overview` (has existing save) | Continue an existing playthrough from the last save point |
| `action:submit-points` | `{ combat: number, intelligence: number, charisma: number, will: number }` | `addPoint` | Finalize character stat allocation |
| `action:start-minigame` | `{}` | `minigameIntro` | Begin the minigame after reading the introduction |
| `action:minigame-complete` | `{ rating: string, score: number }` | `minigamePlaying` | Report minigame completion with grade and score |
| `action:confirm-result` | `{}` | `minigameResult` | Acknowledge minigame results and continue |
| `action:video-end` | `{}` | `plotPreVideo`, `plotPostVideo` | Signal that a narrative video/animation has finished playing |
| `action:select-plot-option` | `{ decisionIndex: number, optionIndex: number }` | `plotSelection` | Select a specific option from the available choices |
| `action:dice-roll` | `{}` | `plotCheck` | Roll the D20 for a stat check |
| `action:go-home` | `{}` | `complete`, `death` | Return to the novel catalog from a terminal phase |
| `action:restart` | `{}` | `complete` | Start a new playthrough of the same novel |
| `action:revive` | `{}` | `death` | Revive the player character (costs currency) |
| `action:open-mall` | `{}` | any phase | Open the in-game store overlay |
| `action:back` | `{}` | `mall` | Close the mall and return to the previous phase |
| `action:logout` | `{}` | any phase | Log out and return to the login phase |

## Game State Queries

The AppCore exposes several methods for querying current game state:

### getData(path) -- Dot-notation State Access

```typescript
app.getData('user.name')           // string: Player's display name
app.getData('user.gems')           // number: Premium currency balance
app.getData('user.coins')          // number: Standard currency balance
app.getData('user.email')          // string: User's email
app.getData('home.novels')         // Novel[]: Array of available novels
app.getData('game.combat')         // number: Combat stat value
app.getData('game.intelligence')   // number: Intelligence stat value
app.getData('game.charisma')       // number: Charisma stat value
app.getData('game.will')           // number: Will stat value
app.getData('game.hp')             // number: Current health points
app.getData('game.san')            // number: Current sanity (0-100)
app.getData('game.xp')             // number: Experience points
app.getData('game.level')          // number: Player level
app.getData('game.inventory')      // Item[]: Items in inventory
app.getData('game.achievements')   // Achievement[]: Earned achievements
```

### getCurrentPhaseId()

Returns the string ID of the current phase (e.g., `"plotSelection"`, `"home"`, `"death"`).

### getStateSnapshot()

Returns a complete state snapshot object with two top-level keys:
- `business` -- All game data (user info, novel state, player stats, economy)
- `control` -- UI state (current phase, navigation stack, loading flags, errors)

## API Client

### ApiClient.ts

Fetch-based HTTP client at `assets/api/ApiClient.ts`. Provides:
- **Auto-token injection:** Automatically includes the authentication token in the `Authorization: Bearer` header for all requests
- **Timeout handling:** Configurable request timeout (default 30 seconds)
- **Error normalization:** Catches network errors and server errors into a consistent format
- **Base URL configuration:** Configurable via constructor parameter

### 6 API Modules

| Module | Description |
|--------|-------------|
| `AuthApi` | Login, register, logout, get current user. Stores and manages the auth token. |
| `NovelsApi` | List novels, get novel details, get story nodes. Provides the content catalog. |
| `SavesApi` | CRUD for player saves. Create, load, update, and delete player state. |
| `GameApi` | Game actions (enterPlot, completePlot, diceRoll, etc.), evaluate choices, check achievements. Core gameplay operations. |
| `MallApi` | Get store catalog, purchase items. Economy interactions. |
| `InventoryApi` | List inventory items, use items, equip items. Player inventory management. |

## Test Infrastructure

### TestRunner.ts -- Home-Built Test Framework

A minimal test framework at `test/TestRunner.ts`. Provides `suite(name, fn)` and `test(name, fn)` functions without any external dependencies (no Jest, no Mocha, no Vitest). Tests are simple async functions that throw on failure. The runner collects results and prints a summary with pass/fail counts and timing.

This custom framework exists because the test environment mocks Cocos Creator APIs at a fundamental level, which creates compatibility issues with standard test frameworks that have their own module systems and global expectations.

### AppGame.ts -- Test Integration Layer

Assembles all three layers (AppCore, EventBus, AppRenderer mock) into a complete testable game instance. Accepts configuration options for backend URL, player settings, and auto-player parameters. Provides convenience methods for common test operations.

### AutoPlayer.ts -- Automated Gameplay Engine

An automated game player that drives the state machine through complete playthroughs without human input. Configuration:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `actionDelay` | number | 800 | Milliseconds between automated actions |
| `maxRounds` | number | 2 | Number of complete game rounds before stopping (0 = infinite) |
| `inviteCode` | string | none | Invite code for account activation |

The AutoPlayer maps each of the 16 phases to an appropriate automated action:

| Phase | Automated Action |
|-------|-----------------|
| `login` | `action:quick-login` (auto-register) |
| `inviteCode` | `action:activate` with configured code |
| `home` | `action:select-novel` (first available novel) |
| `person` | `action:tab-switch` to home |
| `overview` | `action:start-novel` or `action:continue-novel` |
| `addPoint` | `action:submit-points` with balanced stats |
| `mall` | `action:back` |
| `minigameIntro` | `action:start-minigame` |
| `minigamePlaying` | `action:minigame-complete` with random score |
| `minigameResult` | `action:confirm-result` |
| `plotPreVideo` | `action:video-end` |
| `plotSelection` | `action:select-plot-option` (random choice) |
| `plotCheck` | `action:dice-roll` |
| `plotPostVideo` | `action:video-end` |
| `complete` | `action:go-home` (increments round count) |
| `death` | `action:revive` or `action:go-home` |

Round counting: the AutoPlayer increments its round counter when it reaches a terminal phase (`complete` or `death`). When `maxRounds` is reached, it stops. This enables controlled test runs that exercise a specific number of complete story playthroughs.

### cc-mock.ts -- Minimal Cocos Mock

Provides minimal mocks for Cocos Creator APIs required by the AppRenderer layer: `Event` (event dispatching), `Component` (lifecycle hooks), `Node` (scene graph). These mocks are just enough to prevent import errors when loading the full application stack in Node.js. They do not simulate actual rendering.

### 4 Test Suites

| Suite | File | Description |
|-------|------|-------------|
| AppCore | `test/suites/appcore.test.ts` | Tests the pure logic state machine: phase transitions, action processing, state mutations, error handling. Verifies that the AppCore behaves correctly in isolation. |
| PhaseRegistry | `test/suites/phase-registry.test.ts` | Tests phase registration, lookup, and the state machine transition graph. Ensures all 16 phases are correctly registered and transitions are valid. |
| Scenarios | `test/suites/scenarios.test.ts` | End-to-end gameplay scenarios. Tests complete workflows like "login -> select novel -> play through episodes -> complete" against a live backend. |
| UIEvents | `test/suites/ui-events.test.ts` | Tests EventBus event flow between layers. Verifies that action events produce the expected notification events and state changes. |

## Headless Execution

### play.ts -- AutoPlayer CLI

Located at `test/play.ts`. Runs the AutoPlayer from the command line without any Cocos Creator runtime.

```bash
cd "/Users/Clock/moonshort backend/moonshort/test"
npx tsx --tsconfig tsconfig.test.json play.ts
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:3000` | Backend server URL |
| `MAX_ROUNDS` | `2` | Play rounds before stopping (0 = infinite) |
| `ACTION_DELAY` | `800` | Milliseconds between actions |
| `DEBUG` | `true` | Enable EventBus debug logging |

**Timeout:** The play script enforces a 5-minute overall timeout. If the AutoPlayer has not completed within 5 minutes, the process exits with an error.

**Status Snapshots:** Every 15 seconds, the AutoPlayer logs a status snapshot to stdout showing the current phase, round number, player stats, and economy balance. This provides visibility into long-running automated playthroughs.

### run-tests.ts -- Test Suite Runner

```bash
cd "/Users/Clock/moonshort backend/moonshort/test"
npx tsx --tsconfig tsconfig.test.json run-tests.ts
```

Runs all 4 test suites (AppCore, PhaseRegistry, Scenarios, UIEvents) and reports results. Total test count: 49 tests across the 4 suites.

## Backend Integration

The game client connects to the [[entities/moonshort-backend]] at `http://localhost:3000`. Key API interactions:

| Client Operation | Backend Endpoint | Description |
|-----------------|------------------|-------------|
| Quick login | `POST /api/auth/register` | Auto-registers a new account with generated credentials |
| Load novels | `GET /api/novels` | Fetches the catalog of available novels |
| Create save | `POST /api/players` | Creates a new player save for a novel |
| Game action | `POST /api/players/:id/actions` | Executes game actions (enterPlot, completePlot, diceRoll, selectChoice, etc.) |
| Get branches | `GET /api/players/:id/branches` | Loads available story branches at the current position |
| Get narrative | `GET /api/players/:id/narratives` | Loads narrative content for the current story node |
| Mall catalog | `GET /api/mall` | Loads the in-game store catalog |
| Revive | `POST /api/players/:id/revive` | Revives a dead player character |

## Related

- [[entities/moonshort-backend]] -- Backend server that the client connects to
- [[entities/mobai-agent]] -- Orchestrator agent that runs headless tests via CLI gateway
- [[entities/cli-gateway]] -- CLI gateway for remote test execution
- [[concepts/cli-gateway-protocol]] -- HTTP API specification

## Sources

- [Client skill](../raw/2026-04-14-moonshort-client-skill.md)
- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
- [CLI Gateway design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
