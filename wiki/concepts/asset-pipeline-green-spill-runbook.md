---
title: Asset Pipeline — Green-Spill Runbook (recipes for follow-up runs)
updated: 2026-05-09
related:
  - concepts/asset-pipeline-green-spill-fix-2026-05-09
  - concepts/asset-matting-hybrid
---

# Green-Spill Runbook

Recipe-style commands for the follow-up situations after `2026-05-09` G-unspill rollout. See [[concepts/asset-pipeline-green-spill-fix-2026-05-09]] for root-cause analysis.

## Recipe 1: Re-run unspill after a fresh `to-final` (idempotent safety net)

After 2026-05-09 the `rgb_unspill` step is wired into `to-final.py:174` (post `green_spill_clear`). New `to-final` runs auto-unspill. If you suspect drift (e.g. someone reverted the patch or a pipeline produced unspilled files), run:

```bash
cd ~/MobAI/lunaverse-backend
python3 generate-upscale-matting/rgb_unspill.py \
  --root lunascripts/<book-slug>/assets/asset-img-chromakey/ep_sprites \
  --workers 8
python3 generate-upscale-matting/rgb_unspill.py \
  --root lunascripts/<book-slug>/assets/asset-img-chromakey/series \
  --workers 8
# Then re-encode any final.webp that came from unspilled chromakey:
python3 generate-upscale-matting/to-final.py \
  --book-slug <book-slug> --only series,ep1 --overwrite
zsh ... # or python3 -m sync_to_oss --book-slug <slug> --force
```

**Idempotency contract**: rgb_unspill skips any pixel where `G ≤ max(R, B)`, so re-running on already-clean files is a no-op.

## Recipe 2: When `to-final.py` dies mid-pipeline (chromakey ready, final missing)

Post-mortem of 2026-05-09 19:00 incident: `to-final.py` PID was killed silently (no traceback) after `rgb_unspill` finished, before `detect_matting_failures` and webp encoding. `final/<sub>/<id>.webp` was 0 bytes for the 8 javier IDs whose original final had been deleted to force regen.

If chromakey/ PNGs are clean but final/ webp is 0-byte / missing, **don't re-run the whole to-final.py**. Direct PNG→WebP conversion is enough:

```python
from PIL import Image
import pathlib, os

ck = pathlib.Path("lunascripts/<slug>/assets/asset-img-chromakey/<sub>")  # ep_sprites or series
fn = pathlib.Path("lunascripts/<slug>/assets/final/<sub>")
fn1 = fn / "ep1"  # if hardlink layout used
fn1.mkdir(parents=True, exist_ok=True)

for png in ck.glob("*.png"):
    sid = png.stem
    dst1 = fn / f"{sid}.webp"
    if dst1.exists() and dst1.stat().st_size > 0:
        continue
    Image.open(png).convert("RGBA").save(dst1, "WEBP", quality=90, method=4)
    dst2 = fn1 / f"{sid}.webp"
    if dst2.exists(): dst2.unlink()
    os.link(dst1, dst2)  # hardlink
    print(f"✓ {sid}")
```

Then re-run sync_to_oss --force on the affected files.

## Recipe 3: ARG_MAX hit when running chromakey post-processors

`to-final.py` previously called `hole_fill.py`, `green_spill_clear.py`, `rgb_unspill.py` with comma-joined `--paths`. Once the chromakey/ tree exceeds ~1500 PNGs, `paths_arg` exceeds mac `ARG_MAX` (~256 KB) and the shell silently truncates the tail. Symptom: post-processor reports e.g. `targets=1522` while `find <chromakey>/<sub> -name '*.png'` reports 1533. **The lost 11 are unprocessed**, downstream they show up as un-unspilled green-edge sprites.

**Already patched (2026-05-09)** for `rgb_unspill`: to-final.py now passes `--root <chromakey>/<sub>` to rgb_unspill. The fix has not been backported to `hole_fill.py` or `green_spill_clear.py` (they don't support `--root`). For now, the rgb_unspill `--root` walk catches everything those two missed at the G-channel layer, but body holes / opaque dark-green spill on those few sprites might still be uncorrected. Worth adding `--root` to the other two scripts when convenient.

## Recipe 4: Run MODNet full-book to recover hair detail (the deferred upgrade)

The `cutout.py feather=0.8` HSV chromakey loses ~5-15% of hair edge softness on i2i sprites — visible as "悬空发丝" (floating hair strands not connected to head silhouette). G-unspill can't recover this because the alpha is already cropped.

To run MODNet on every sprite + character series (~7 hours CPU on M2 Pro for ~1500 sprites, can be background-overnight):

```bash
cd ~/MobAI/lunaverse-backend

# Verify MODNet is installed (run once):
python3 -c "import sys; sys.path.insert(0, 'generate-upscale-matting'); from matting import matte_one; print('MODNet ✓')"
# If fails: see generate-upscale-matting/matting.py:30-40 for setup_matting_env.sh

# Force-FAIL all sprites so detect_matting_failures.py routes everything to MODNet.
# Easiest: stash the existing report, write a synthetic FAIL-everything report.
RPT=lunascripts/new-no-rules-in-bad-ideas/assets/asset-img-chromakey/detect_report.json
[ -f $RPT ] && cp $RPT $RPT.bak
python3 - <<'PY'
import json, pathlib
ck = pathlib.Path("lunascripts/new-no-rules-in-bad-ideas/assets/asset-img-chromakey")
results = {}
for sub in ("series", "ep_sprites"):
    for png in (ck / sub).glob("*.png"):
        results[png.stem] = {"verdict": "FAIL", "holes_pct": 0, "body_gap_px": 0, "path": str(png)}
out = {"results": results}
(ck / "detect_report.json").write_text(json.dumps(out))
print(f"wrote synthetic FAIL report for {len(results)} files")
PY

# Now run to-final.py — it'll see all FAIL and route to MODNet.
nohup python3 generate-upscale-matting/to-final.py \
  --book-slug new-no-rules-in-bad-ideas \
  --only series,ep1 \
  --overwrite \
  > logs/to-final-modnet-full-$(date +%F).log 2>&1 &
disown

# After done (~7 hours), restore the real detect report so future runs don't re-MODNet.
mv $RPT.bak $RPT  # if you want detect to run fresh next time, just `rm $RPT`

# Then sync to OSS.
nohup python3 generate-upscale-matting/_local_tools/sync_to_oss.py \
  --book-slug new-no-rules-in-bad-ideas --force --workers 10 \
  > logs/oss-sync-modnet-$(date +%F).log 2>&1 &
disown
```

**Expected MODNet output quality** (verified on selena ep1 BEAT-1 single-frame test):

| Metric | chromakey + unspill | MODNet + unspill |
|---|---|---|
| Hair detail vs RAW | ~85% | ~98% |
| Edge mean G | 65 | 44 |
| Interior leak | 0 | 0 |
| Floating hair strands | yes (visible) | no |
| Soft alpha pixel count | 28k | 20k (sharper but cleaner) |

**Trade-off**: MODNet's `alpha_sharpen` step (`matting.py:lo=32,hi=192` linear remap) gives sharper hair edges but loses some natural softness vs chromakey feather. Acceptable for VN UI rendering on solid backgrounds.
