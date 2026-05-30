---
name: dream-bonus-only-and-feed-skip-design
description: 2026-05-25 brainstorm spec — replace 3 v1 dream entry-patch ops with single bonus_only + feed skip-to-E1
source_repo: cdotlock/moonshort-backend
source_files:
  - docs/superpowers/specs/2026-05-25-dream-bonus-only-and-feed-skip-design.md
fetched: 2026-05-30
status: source-of-truth-mirror
---

# Dream bonus_only OP — Source Mirror (2026-05-30)

Mirror of upstream brainstorming spec. Wiki synthesis: [[concepts/dream-bonus-only-op]].

## Source

[`docs/superpowers/specs/2026-05-25-dream-bonus-only-and-feed-skip-design.md`](https://github.com/cdotlock/moonshort-backend/blob/main/docs/superpowers/specs/2026-05-25-dream-bonus-only-and-feed-skip-design.md) — ≈376 行，Clock + Claude brainstorm 2026-05-25 出，2026-05-26+ 实施。

## Quoted goals

> 1. Suppress all three current OP types in the **production** pipeline: the planner cannot pick them, the entry-patch specialist cannot author them, and the storage / wire validators reject them.
> 2. Introduce a single new OP — **`bonus_only`** — with a tightly constrained shape: terminal placement, template "Continue" option, LLM-authored flavor for the dream option, mechanical routing.
> 3. Skip the source-episode walkthrough when the player taps a dream card on the Home Feed: the transient replay session starts directly at the dream's E1.
> 4. Wipe legacy dreams (those whose `entryPatch.operations[].op` is one of the three suppressed types) from production so the new path is the only path a player encounters.

## bonus_only wire shape

```jsonc
{
  "op": "bonus_only",
  "optionFlavor": "Step through the silvered mirror."
}
```

Exactly two fields. Schema enforces `optionFlavor` min(1).max(120). `operations[]` must contain exactly one element when any op is `bonus_only` (`.refine`).

## No-mainline-mutation invariant

Dream MSS source under `bonus_only` MUST NOT emit:
- `@affection <character> <delta>`
- `@signal mark <event>` / `@signal int <name> <op> <value>`
- `@butterfly <description>`
- `@achievement <id>`

Three-layer defense: writer prompt (Iron Rule), reviewer prompt (`dream_mainline_mutation_forbidden` kind), backend `services/dream-agent/src/validation.ts` content-walk (severity `critical`).

## Cleanup script

`scripts/cleanup-legacy-dream-ops.ts` — default dry-run, `--apply` mutates. Deletes legacy Dreams + their DreamAssignments + orphan transient sessions. **Script must be deleted from main after one successful run** (footgun ammo).

For full spec, read source above.
