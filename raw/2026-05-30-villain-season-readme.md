---
name: villain-season-readme
description: Heart Signal otome NA short — moonshort-backend demo / platform showcase / new-player tutorial
source_repo: cdotlock/moonshort-backend
source_files:
  - moonscripts/villain-season/README.md
fetched: 2026-05-30
status: source-of-truth-mirror
---

# Villain-Season README — Source Mirror (2026-05-30)

Mirror of in-repo README. Wiki synthesis: [[concepts/villain-season-demo]].

## Source

[`moonscripts/villain-season/README.md`](https://github.com/cdotlock/moonshort-backend/blob/main/moonscripts/villain-season/README.md)

## Quoted summary

> Heart Signal 设定下的 NA otome 短剧 + 平台功能 demo。3 集 + 1 dream，端到端展示当前所有 player-facing 机制。**双重用途**：新玩家教学 + 投资人演示。
>
> **现在是两本平行 novel，行为完全一致**（同一套素材 / 同 dream 链 / 同成就 / 同小游戏）：

| novelId | 语言 | 配音 |
|---|---|---|
| `villain-season` | 英文 | ✅ 英文 Breeze 配音 + TTS 已生产 |
| `villain-season-zh` | 中文 | ❌ 无（目前只有英文 TTS） |

## One-command seed

```bash
pnpm seed:villain-season:full     # build + seed 两本
```

Sub-commands: `:en` / `:zh`.

## Verify

```bash
pnpm verify:villain-dream
```

End-to-end assertions on both novels including **real createSession runtime auto-mount**.

## Forced dream pattern

`Dream.entryPatch` has two flags:
- `autoAssign: true` — `app/services/dream-autoassign-service.ts` 在 `createSession` post-commit 自动挂 DreamAssignment
- `operations: [{ op: "bonus_only", optionFlavor: ... }]` — runtime 追加 Continue + ✦DREAM 选项

For full file list / asset inventory / mechanism coverage table / TTS pipeline / 教学层 配比 / 已知局限, read source above.
