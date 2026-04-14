---
name: moonshort-game-client
description: Moonshort Cocos Creator game client — AppCore state machine, test framework, AutoPlayer
triggers: ["moonshort", "cocos", "client", "game-client", "phase", "AppCore", "AutoPlayer", "前端", "客户端", "状态机"]
autoload: false
priority: 10
---

# Moonshort Game Client — Cocos Creator Frontend

Pure-logic game state machine testable from Node.js (no Cocos runtime needed).

## Architecture

- **Location**: `/Users/Clock/moonshort backend/moonshort/`
- **Engine**: Cocos Creator 3.8.8 (but core logic is Cocos-free)
- **Pattern**: AppCore (logic) + EventBus (pub/sub) + AppRenderer (Cocos UI)
- **Test Interface**: `/test/` directory with cc-mock.ts for Node.js execution

## Running Tests

```bash
cd "/Users/Clock/moonshort backend/moonshort/test" && npx tsx --tsconfig tsconfig.test.json run-tests.ts
```

## Running AutoPlayer (automated gameplay)

```bash
cd "/Users/Clock/moonshort backend/moonshort/test" && npx tsx --tsconfig tsconfig.test.json play.ts
```

Options (env vars):
- `BASE_URL` — Backend server (default: http://localhost:3000)
- `MAX_ROUNDS` — Play rounds before stopping (default: 2, 0=infinite)
- `ACTION_DELAY` — ms between actions (default: 800)
- `DEBUG` — Enable EventBus debug logging (default: true)

## Phase State Machine (15 phases)

```
login → [inviteCode] → home → person/overview → addPoint → mall
                                    ↓
                        minigameIntro → minigamePlaying → minigameResult
                                    ↓
                        plotPreVideo → plotSelection → plotCheck → plotPostVideo
                                    ↓
                        complete / death → (restart/revive) → home
```

## EventBus Action Events (how to drive the game)

| Action | Payload | Phase Context |
|--------|---------|---------------|
| `action:quick-login` | `{}` | login |
| `action:login` | `{username, password}` | login |
| `action:activate` | `{inviteCode}` | inviteCode |
| `action:select-novel` | `{novelId}` | home |
| `action:tab-switch` | `{target: 'home'\|'person'}` | home/person |
| `action:start-novel` | `{}` | overview (no saves) |
| `action:continue-novel` | `{}` | overview (has saves) |
| `action:submit-points` | `{combat,intelligence,charisma,will}` | addPoint |
| `action:start-minigame` | `{}` | minigameIntro |
| `action:minigame-complete` | `{rating,score}` | minigamePlaying |
| `action:confirm-result` | `{}` | minigameResult |
| `action:video-end` | `{}` | plotPreVideo/plotPostVideo |
| `action:select-plot-option` | `{decisionIndex,optionIndex}` | plotSelection |
| `action:dice-roll` | `{}` | plotCheck |
| `action:go-home` | `{}` | complete/death |
| `action:restart` | `{}` | complete |
| `action:revive` | `{}` | death |
| `action:open-mall` | `{}` | any |
| `action:back` | `{}` | mall |
| `action:logout` | `{}` | any |

## Querying Game State

```typescript
app.getData('user.name')        // Player username
app.getData('user.gems')        // Premium currency
app.getData('home.novels')      // Novel list
app.getData('game.combat')      // Combat stat
app.getData('game.san')         // Sanity (0-100)
app.getCurrentPhaseId()         // Current phase
app.getStateSnapshot()          // Full state {business, control}
```

## Integration with Backend

The game client connects to the backend at `http://localhost:3000`. Key API calls:
- `POST /api/auth/register` — Quick login (auto-registers)
- `GET /api/novels` — Load novel catalog
- `POST /api/players` — Create save
- `POST /api/players/{id}/actions` — Game actions (enterPlot, completePlot, etc.)

## Testing Specific Scenarios

To test a specific game flow, you can write a script that:
1. Creates an AppGame with desired config
2. Listens for phase-change events
3. Emits specific action events at the right time
4. Asserts state after transitions

Example via bash tool:
```bash
cd "/Users/Clock/moonshort backend/moonshort/test" && npx tsx --tsconfig tsconfig.test.json -e "
import { AppGame } from './AppGame';
const game = new AppGame({ baseUrl: 'http://localhost:3000', autoPlayer: { maxRounds: 1 } });
game.bus.on('notify:phase-change', ({from, to}) => console.log(from, '→', to));
await game.start();
setTimeout(() => { console.log(JSON.stringify(game.app.getStateSnapshot(), null, 2)); process.exit(0); }, 30000);
"
```
