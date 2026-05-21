---
title: ComfyUI on Modal — matting + upscale-image serverless deploy
updated: 2026-05-21
tags: [assetctl, comfyui, modal, deploy, pattern-b, infrastructure]
---

# ComfyUI on Modal — `matting` + `upscale-image` serverless deploy

**One-line**: Single Modal app exposes two HTTP endpoints that satisfy the existing assetctl Pattern B Go contract for `matting` (BiRefNet) and `upscale-image` (Real-ESRGAN), with output uploaded to Aliyun OSS — IDE-side env vars are the only client change.

## Why this concept exists

The Go-side atomic tools `matting` and `upscale-image` already POST to `FC_MATTING_URL` / `FC_UPSCALE_IMAGE_URL` per the [[concepts/assetctl-integration-contract]]. Until 2026-05-21 there was **no backend** behind those env vars. This deploy fills that gap **without touching Go code** by standing up ComfyUI inside a Modal app whose `@modal.fastapi_endpoint` URLs are pointed to by those env vars.

## What's in this deploy

| Slot | Choice | Why |
|---|---|---|
| Serverless platform | **Modal** | Only mainstream serverless GPU platform that supports **native sync HTTP up to 600s** matching the Go-side timeout. Free $30/mo credit covers the single-developer case end to end. |
| Matting model | **BiRefNet_toonOut** (default), BiRefNet_HR-matting (fallback) | Anime-trained, open license (vs. BRIA RMBG-2.0's commercial license), clean alpha on character art. Node pack: `1038lab/ComfyUI-RMBG`. |
| Upscale model | **RealESRGAN_x2plus** (scale=2), **RealESRGAN_x4plus_anime_6B** (scale=4 default), **4x-AnimeSharp** (optional) | Anime-trained Real-ESRGAN variants; standard for character art, small weights, fast on A10. |
| GPU | A10 (default), A100-40GB headroom | $0.0003/s on Modal; BiRefNet + Real-ESRGAN both fit comfortably. |
| Output storage | Aliyun OSS, key `<bucket>/<slug>/<assetName>.<ext>` | Matches the OSS key suggestion in handoff doc §2.3 + keeps URL semantics identical to the other Pattern B tools so downstream `oss-put` / mapping.json logic is unchanged. |

## Key contracts (don't drift)

- **Field order locked** in both request bodies (handoff doc §2.3.2 / §2.3.3). Pydantic models in `app.py` must match Go-side struct tag order.
- **Response selector**: Go calls `fc.ExtractURL(raw, "imageUrl", "url", "result")` — return at least `imageUrl`.
- **Error mapping**: 401/4xx → `CodeInvalidInput` (no retry); 429/5xx → `CodeTransient` (retry). Response body ≤ 500 bytes (Go truncates).
- **Two distinct Bearer tokens**: `FC_MATTING_TOKEN` and `FC_UPSCALE_IMAGE_TOKEN`. Leak isolation; cost is 32 bytes of randomness.
- **Modal timeout 600s** ↔ ComfyUI internal cap 540s — 60s headroom so the response gets to write a proper 500 instead of socket reset.

## What's out of scope (don't add without re-design)

- `cg-render`, `nrbi-render-prompt`, and the six older Wave 1/2 tools — owned by separate deploy work.
- **v10 post-process** (green-screen unmix + alpha sharpen tuned for 1882×3344 from the donor MODNet pipeline). BiRefNet output alpha is clean enough; downstream `green-spill-clear` + `rgb-unspill` in assetctl handle green-screen residue. Revisit only if donor reference set shows quality regression.
- Multi-tenant; UI / dashboard; per-user rate limiting.

## Repo layout

```
moonshort-ide/
├── docs/design/2026-05-21-comfyui-modal-deploy-spec.md   # the spec
├── docs/handoff/2026-05-21-fc-endpoint-backend-deploy-spec.md  # wire contract source-of-truth
├── modal-comfy/         # new; ~300 LOC Python + 2 workflow JSON
│   ├── app.py
│   ├── comfy_runner.py
│   ├── workflows/{matting,upscale}.json
│   ├── oss_upload.py
│   ├── validators.py
│   └── tests/
└── vendor/assetctl/internal/tools/{matting,upscaleimage}/  # Go client, NO change
```

`modal-comfy/` is a sibling of `vendor/assetctl/`, never mixed into the Go module tree.

## Deployment runbook (short)

```bash
# (once) install + auth + secrets
pip install modal && modal token new
modal secret create alibaba-oss OSS_ACCESS_KEY_ID=... ...
modal secret create moonshort-fc-token \
    FC_MATTING_TOKEN=$(openssl rand -hex 32) \
    FC_UPSCALE_IMAGE_TOKEN=$(openssl rand -hex 32)

# (per change) deploy
cd modal-comfy && modal deploy app.py

# (IDE side) set 4 env vars: FC_MATTING_URL/TOKEN + FC_UPSCALE_IMAGE_URL/TOKEN
# (verify) handoff-doc §6 commands:
cd ../vendor/assetctl
go run ./cmd/assetctl run matting --input '{...}'
go run ./cmd/assetctl run upscale-image --input '{...}'
```

Full runbook + costs + testing matrix: see [`docs/design/2026-05-21-comfyui-modal-deploy-spec.md`](https://github.com/cdotlock/moonshort-ide/blob/feat/assetctl-foundation/docs/design/2026-05-21-comfyui-modal-deploy-spec.md).

## Related

- [[concepts/assetctl-integration-contract]] — Pattern B HTTP transport + 18 atomic-tool surface
- [[concepts/asset-matting-hybrid]] — the A (chromakey) + B (ML) split; this deploy is the ML side
- [[concepts/codex-runtime-and-verification-layers]] — how this fits the L0/L1/L2 verification stack
