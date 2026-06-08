---
title: to-final.py _raw Cache Trap
tags: [asset-pipeline, bug, n2m, lunaverse-backend]
date: 2026-05-10
---

# `to-final.py` `_raw` Cache Trap

**Discovered:** 2026-05-10 during tier-A remi resprite (NRBI book, 23 sprites).

## Symptom

After re-rendering a sprite (Task 5 → fresh `gen-upscale/<name>.png`,
Task 6 → `gen-upscale/<name>_upscaled.png`), `to-final.py` produces a final
webp containing the **OLD** sprite content, not the new render.

Visual signature for the NRBI tier-A case: new gen-upscale shows correct curly
remi, OSS-served webp still shows old broken remi (long bangs, gold choker).

## Root Cause

`lunaverse-backend/generate-upscale-matting/to-final.py:160-167`:

```python
for src in targets:                         # gen-upscale upscaled.png (NEW)
    raw_copy = raw_dir / src.name           # asset-img-chromakey/_raw/<name>.png
    if not raw_copy.exists():               # ← only copies if backup MISSING
        shutil.copy2(src, raw_copy)
    if not chromakey_png.exists() or overwrite:
        shutil.copy2(raw_copy, chromakey_png)  # copies from raw_copy, not src
```

Once `_raw/<name>.png` exists from any earlier run, the script **skips**
updating it. All downstream stages (cutout, hole_fill, green_spill,
rgb_unspill, webp encode) then process the **stale backup content** instead
of the freshly rendered upscaled PNG.

## Detection

```bash
RAW=asset-img-chromakey/_raw/ep_sprites/<name>.png
SRC=gen-upscale/ep_sprites/<name>_upscaled.png
[[ "$RAW" -ot "$SRC" ]] && echo "TRAP ACTIVE: stale _raw backup"
```

If timestamps differ, the trap is active for that sprite.

## Workaround Before Re-running `to-final.py`

Delete stale backups for affected sprites:

```bash
ASSETS=lunascripts/<book-slug>/assets
while read base; do
  rm -f "$ASSETS/asset-img-chromakey/_raw/ep_sprites/${base}.png"
  rm -f "$ASSETS/asset-img-chromakey/ep_sprites/${base}.png"
done < broken-basenames.txt
```

Then `to-final.py --only ep1` will copy fresh content from gen-upscale.

## Fast Manual Path (skip full pipeline scan)

For small batches (≤50 sprites), skip the 50-min full to-final.py rerun
(cutout/hole_fill/spill/unspill all process all 1500+ sprites).

```bash
cd /Users/august/MobAI/lunaverse-backend
ASSETS=lunascripts/<book-slug>/assets
GU=$ASSETS/gen-upscale/ep_sprites
RAW=$ASSETS/asset-img-chromakey/_raw/ep_sprites
CK=$ASSETS/asset-img-chromakey/ep_sprites

# 1. Stage new content (drops _upscaled suffix)
while read base; do
  cp "$GU/${base}_upscaled.png" "$RAW/${base}.png"
  cp "$GU/${base}_upscaled.png" "$CK/${base}.png"
done < /tmp/basenames.txt

# 2. cutout with --only filter
ONLY=$(tr '\n' ',' < /tmp/basenames.txt | sed 's/,$//')
python3 generate-upscale-matting/cutout.py \
  --root $ASSETS/asset-img-chromakey --only "$ONLY" --force

# 3. hole_fill / green_spill / rgb_unspill via --paths
PATHS=""
while read b; do
  [[ -n "$PATHS" ]] && PATHS="$PATHS,"
  PATHS="$PATHS$(pwd)/$CK/${b}.png"
done < /tmp/basenames.txt

python3 generate-upscale-matting/hole_fill.py --paths "$PATHS"
python3 generate-upscale-matting/green_spill_clear.py --paths "$PATHS"
python3 generate-upscale-matting/rgb_unspill.py --paths "$PATHS"

# 4. WebP encode (replicates to-final.py:271-285 + _inline_unspill)
python3 - <<'PY'
import pathlib, numpy as np
from PIL import Image
def inline_unspill(im):
    arr = np.array(im).copy()
    if arr.shape[-1] != 4: return im
    R, G, B, A = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    rb_max = np.maximum(R, B)
    mask = (A > 0) & (G > rb_max)
    arr[..., 1] = np.where(mask, rb_max, G)
    return Image.fromarray(arr, "RGBA")

ck = pathlib.Path("<ASSETS>/asset-img-chromakey/ep_sprites")
fd = pathlib.Path("<ASSETS>/final/ep_sprites")
fd.mkdir(parents=True, exist_ok=True)
for base in pathlib.Path("/tmp/basenames.txt").read_text().split():
    im = inline_unspill(Image.open(ck / f"{base}.png").convert("RGBA"))
    im.save(fd / f"{base}.webp", "WEBP", quality=90, method=6)
PY
```

For 23 sprites the manual path took ~2 min vs ~50 min full rerun.

## Permanent Fix (TODO)

Patch `to-final.py:164` to compare timestamps:

```python
if not raw_copy.exists() or src.stat().st_mtime > raw_copy.stat().st_mtime:
    shutil.copy2(src, raw_copy)
```

Or always re-copy when `--overwrite`. Filed for next pipeline maintenance.

## Related

- `2026-05-08-asset-coverage-guarantee-phase-6-handoff.md` — render-with-style
  produces RGBA, but to-final still runs full chromakey/spill pipeline
- `concepts/asset-pipeline-green-spill-fix-2026-05-09` — companion green-spill
  story that also lives in this directory
