---
title: Moonshort Backend
tags: [nextjs, game-engine, prisma, postgresql]
sources: [raw/2026-04-14-mobai-agent-memory.md]
created: 2026-04-14
updated: 2026-04-14
---

Next.js full-stack application serving as the game engine and admin dashboard for Moonshort interactive fiction games. Handles player state, story delivery, achievements, payments, and character chat.

## Tech Stack

- **Framework:** Next.js 16
- **DB:** PostgreSQL (Prisma ORM v6.6)
- **Auth:** NextAuth v5 (Google OAuth + email/password)
- **Payments:** Stripe
- **LLM:** OpenAI-compatible (remix, character chat)
- **Observability:** Langfuse
- **Repo:** github.com/Rydia-China/noval.demo.2

## API Surface (85+ routes)

- `/api/players/*` — Player state, actions, branches, narratives
- `/api/novels/*` — Story delivery from upstream
- `/api/game/*` — Evaluate choices, dice checks, achievements
- `/api/remix/*` — User-generated story branches via LLM
- `/api/character-chat/*` — NPC chat with LLM
- `/api/stripe/*` — Payment processing
- `/api/admin/*` — Content management

## CLI: noval

Standalone TypeScript CLI (`cli/bin/noval.ts`, Commander.js). Commands: `sync`, `list`, `play`, `show`, `remix`, `chat`, `topup`, `import`, `config`. Supports `--auto` mode for automated testing and `--json` for structured output.

## Game Systems

- **D20 dice** — Skill checks with combat/intelligence/charisma/will stats
- **Economy** — Coins + gems currency
- **Survival** — HP + SAN (sanity) meters
- **Minigames** — Score-based grade system (S/A/B/C/D)
- **Achievements** — Type 1 (milestone), Type 2 (story), Type 3 (collection)

## Related

- [[entities/mobai-agent]]
- [[entities/moonshort-client]]
- [[concepts/cli-gateway-protocol]]

## Sources

- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
