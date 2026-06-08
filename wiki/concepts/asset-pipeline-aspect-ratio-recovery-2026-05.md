---
title: "Asset Pipeline Aspect-Ratio Recovery (NRBI 2026-05)"
description: "Root-cause analysis + recovery playbook for the May 2026 NRBI asset pipeline drift: mob-ai aspect-ratio non-determinism, render-without-resync footgun, and the cascade re-render strategy."
tags: ["asset-pipeline", "render-with-style", "mob-ai", "incident", "playbook"]
---

# Asset Pipeline Aspect-Ratio Recovery (NRBI 2026-05)

## Context

In May 2026 the NRBI (No Rules in Bad Ideas) asset pipeline was found to be silently producing visually inconsistent character / anchor / sprite images. The visible symptom was *upscaled* PNGs whose face/identity didn't match the *non-upscaled* version sitting next to them — most obviously on `weston`, `mariana`, and `remi`. Root-cause investigation found three independent failure modes that compounded.

This page documents what went wrong, the fix shipped on 2026-05-09, and the operational playbook so future drift can be detected and recovered without another full investigation.

## Root cause #1 — mob-ai image-gpt aspect-ratio non-determinism

`render-with-style.py` (in `lunaverse-backend/generate-upscale-matting/`) calls the mob-ai image-gpt API with the prompt body containing a soft-constraint phrase like `"竖构图全身立绘，9:16"`. Two empirical findings:

1. **The API silently ignores all body-level size hints.** A discriminating probe (`_local_tools/probe_mob_ai_size.py`) tested 6 schema hypotheses — `aspect_ratio`, `size`, `width`+`height`, both nested under `input` and at top level — by requesting `16:9` while the prompt asked for vertical. ALL 6 variants returned vertical output, proving the body-level hint never reaches the model. The API server appears to discard unknown fields silently, with no error.
2. **Pure-prompt control hits a ~13% drift rate.** With only the prompt asking for 9:16, the model returns the requested 941×1672 (ratio 0.5625) most of the time, but ~13% of requests fall back to the 1024×1536 (2:3, ratio 0.667) default. A handful (~1%) come back as 1024×1024 (1:1).

Why this matters: the downstream chromakey + matting + sprite-binding chain assumes a 9:16 portrait. When a sprite is rendered at 1024×1536 the bounding box / face position / anchor reference no longer compose correctly with sibling sprites in the episode.

### Fix: client-side aspect-ratio retry guard (Phase 4)

Patched `render_with_retry()` in `render-with-style.py` to validate the returned PNG's dimensions against a per-category expected aspect ratio (±3% tolerance) before writing to disk. If the ratio is wrong, the image is discarded and the call retries up to `MAX_RETRIES=3` with a `RETRY_DELAY_S=5` backoff between attempts.

Per-category expected ratios:

```python
_EXPECTED_ASPECT_BY_CATEGORY = {
    CHAR_SERIES_CATEGORY:   9 / 16,  # 0.5625 — character series
    OUTFIT_ANCHOR_CATEGORY: 9 / 16,  # outfit anchors
    CHAR_EP_CATEGORY:       9 / 16,  # ep sprites
    SCENE_GRID_CATEGORY:    1.0,     # scene grids (square)
    SCENE_SERIES_CATEGORY:  1.0,     # scene series (square)
}
_ASPECT_TOLERANCE = 0.03
```

With a 13% per-attempt drift rate, 3 attempts gives `1 - 0.13^3 ≈ 99.78%` first-write success. The `aspect_drift_after_3_attempts` failure case shows up in the run summary so we know which IDs need a rerun.

## Root cause #2 — render-without-resync (operational footgun)

`upscale.py`'s skip-if-exists logic was originally `if dst.exists() and not overwrite`. This made the steady-state upscale loop fast (already-upscaled stays upscaled), but created a footgun the first time a 1× was re-rendered without `--overwrite`:

1. `render-with-style.py` re-renders `character_<id>.png` at 18:27 (new content).
2. `upscale.py` is run; `character_<id>_upscaled.png` already exists → "skip".
3. The `_upscaled` PNG still holds the 03:09 batch's content. It now silently disagrees with the 1× sitting next to it.
4. `to-final.py` chromakey-mattes the stale `_upscaled` and writes `final/series/character_<id>.webp` — the published deliverable diverges from the 1× source.

This is what produced the original `weston` / `mariana` / `remi` "upscaled is a different image" symptom. 13 of 15 NRBI characters had `MAE(1×, _upscaled_downsampled)` between 60 and 82 — a completely different image, not just a noisy upscale.

### Fix: mtime-aware skip in `upscale.py`

```python
if dst.exists() and not overwrite:
    try:
        if src.stat().st_mtime <= dst.stat().st_mtime:
            return ("skip", str(dst.name), 0.0)
        # else: src is newer → fall through and re-upscale (auto-staleness)
    except OSError:
        return ("skip", str(dst.name), 0.0)
```

Now a re-render of the 1× source automatically invalidates the `_upscaled` companion on the next `upscale.py` run, even without `--overwrite`. Operationally, this means "re-render → re-upscale → re-final" is the default path, and you only fall through to skip when both files are at the same generation.

## Root cause #3 — sprite hardlink design is fine but had to be re-explained

`skip_upscale_ep_sprites.sh` hardlinks `<id>_upscaled.png` to `<id>.png` for ep sprites — the user's laptop can't run Real-ESRGAN over 1500 sprites in any reasonable timeframe (~16h), so we skip the upscale step for sprites and ship them at their native 1× resolution. This is intentional, not a bug.

It was confused with #2 during initial investigation because the symptom (`_upscaled` and 1× being different) looked the same. The disambiguation: for series characters the `_upscaled` should be 2× content of the 1×; for ep sprites the `_upscaled` is literally the same inode as the 1×.

## Recovery playbook (NRBI 2026-05-09)

The 2026-05-09 recovery executed the following tiered strategy after the user clarified that only the LI characters needed full cascade re-render. Total cost ≈ \$30, total time ≈ 1.5 hours wall-clock.

### Tiered scope

| Asset | Total | Strategy |
|---|---|---|
| character series 1× / _upscaled / final | 15 | 7 chars copied from human-reviewed `~/Downloads/lunascripts/no-rules-in-bad-ideas/` Downloads set; 8 chars left as-is (already 9:16 from 18:27 re-render, _upscaled drift accepted) |
| outfit anchor | 79 | LI cascade for diego / luca / mariana / weston (17 anchors); spot-fix 2 ratio-broken non-LI (remi_casual_default + xiomara_casual_default); other 60 left as-is |
| ep sprite | 1594 | LI cascade for diego / luca / mariana / weston (887 task entries → 667 unique); spot-fix 82 ratio-broken non-LI (camila / brielle / elena / hector / etc.); other 845 left as-is |

The non-cascaded supporting characters (selena MC + camila / xiomara from Downloads + 8 non-Downloads supporting cast) accept slight face drift between `final/series/character_<c>.webp` and the existing anchor/sprite renders, because the existing anchor/sprite output looks fine in practice and re-rolling the 1594 i2i renders has a higher expected-bad-output cost than the cosmetic mismatch.

### Why full LI cascade (not just ratio-broken)

Anchors are `Layer A.5` i2i renders that bind `character_<char>.png` as primary reference. Sprites are `Layer E` i2i renders that bind `series/anchors/<char>_<outfit>.png` as primary reference (with character fallback). Replacing a character ref means every anchor/sprite downstream of it has a different face on i2i seed → if we keep the old anchor/sprite, the player would see character.webp showing one face but sprite.webp showing a different face. Same character, two visual identities. Worse than the original drift bug.

### Execution order (must be sequential)

1. **Replace** 5 chars from Downloads (gen-upscale 1× + _upscaled + final.webp directly copied — no re-render needed; Downloads versions are already RGB-on-green).
2. **Backup + delete** the 19 target anchors.
3. **Re-render** 19 anchors via `render-with-style --only anchor:<id>,...` — the retry guard ensures all hit 9:16. Visual sample-check after.
4. **Backup + delete** the 667 unique target sprites + their `_upscaled` hardlinks + `_raw/` + `chromakey/` + `final/` derivatives.
5. **Re-render** sprites via `render-with-style --only sprite:<id>,...` — Layer E binding picks up the new anchors from step 3. Visual sample-check after.
6. **Recreate** sprite hardlinks via `skip_upscale_ep_sprites.sh`.
7. **Re-derive** final.webp via `to-final.py --book-slug <slug>` — chromakey + cutout + matting + WebP convert.
8. **Verify** all 15 characters / 79 anchors / 1594 sprites at 9:16 ±3% and confirm spot-checked content alignment.

Sprite re-render must come AFTER anchor re-render. If sprites render first they would i2i against the OLD anchors (still on disk) → cascade is lost.

## Out-of-scope follow-ups

1. **Real-ESRGAN re-upscale** of the 8 non-Downloads chars (jared / javier / mj / mr_bellamy / mrs_ashby / priya / remi / sofia). Their _upscaled.png still holds 03:09 batch content. User defers until laptop has cycles for the ~16h overnight run. The mtime patch from #2 will trigger this automatically once `upscale.py --only series` is run.
2. **OSS sync** of the new final.webp deliverables to Aliyun bucket `mobai-file/nrbi/`. Operational task post-recovery.

## Lessons / contracts

- **Soft prompt constraints don't replace client-side validation** when the upstream API silently discards fields. If a constraint matters for downstream stability, validate the response and retry on violation. This is true for image dimension, color space, file format, anything mob-ai's API can drift on.
- **`exists()` is not a freshness check.** Any pipeline step that derives `dst` from `src` should compare mtimes (or content hashes) before claiming "skip". The `dst.exists() and not overwrite` pattern is fine for read-only outputs but creates silent drift the moment the input gains a new generation.
- **Cascade dependencies need to be explicit in re-render scope.** Replacing a series character without re-rendering its anchors is silently broken. The fact that anchors are i2i refs to character is encoded only in `_bind_series_portrait_for_anchor` source — there's no operational warning on disk. Future improvement: `render-with-style.py` could read a `--cascade <char>` flag that auto-expands to all anchors + sprites bound to that character.

## Related

- Plan: `docs/superpowers/plans/2026-05-09-aspect-ratio-recovery.md` (in `~/MobAI/novels-to-lunascript`)
- Probe results: `~/MobAI/lunaverse-backend/_local_tools/probe_mob_ai_size_result.json`
- Backup directory: `~/MobAI/lunaverse-backend/lunascripts/new-no-rules-in-bad-ideas/assets/_backup_2026-05-09_pre-aspect-fix/`
- Logs: `~/MobAI/lunaverse-backend/logs/anchor-rerender-2026-05-09.log`, `logs/sprite-rerender-2026-05-09.log`
- Project CLAUDE.md `Addendum (2026-05-08)` confirms render-with-style now outputs RGBA for sprites — applies to Layer E only; anchors (Layer A.5) stay RGB on green as i2i refs.
