---
title: Mob AI Router
tags: [gateway, llm, api, openai-compatible, embeddings, rerank, image, video, jina, claude, deepseek, gpt]
sources: [raw/2026-05-25-mob-ai-router-integration.md]
source_url: https://ai.mob-ai.cn/integration.html
created: 2026-05-28
updated: 2026-05-28
---

Public-facing LLM router that fronts Claude, DeepSeek, GPT, Jina, and image / video providers behind a single OpenAI-compatible HTTP surface. All Lunaverse services that need a foundation model talk to this router instead of provider-native APIs, so virtual keys, quota, billing, and provider failover are managed in one place. Canonical machine-readable integration guide is the upstream HTML page at <https://ai.mob-ai.cn/integration.html> (mirrored verbatim into [raw/2026-05-25-mob-ai-router-integration.md](../raw/2026-05-25-mob-ai-router-integration.md), upstream last-modified 2026-05-25).

## Endpoint Surface

- **Public base URL:** `https://ai.mob-ai.cn/api`
- **Auth:** `Authorization: Bearer <mob-virtual-key>` — every endpoint takes the same `mob-`-prefixed virtual key. **Never** pass a provider-native key (OpenAI / Anthropic / etc.) through this router.

| Capability | Endpoint | Notes |
|---|---|---|
| List models | `GET /v1/models` | catalogue lookup / smoke test |
| Chat | `POST /v1/chat/completions` | OpenAI-compatible; most models take `max_tokens`. `gpt-5.5-pro` also accepts `max_completion_tokens`. |
| Responses | `POST /v1/responses` | Used for `gpt-5.5:free`. Single `input` field (not `messages`). |
| Embeddings | `POST /v1/embeddings` | Jina route; response is `data[0].embedding`. Supports `task`, `dimensions`, `late_chunking` passthrough. |
| Rerank | `POST /v1/rerank` | Jina route; returns ranked array with `index` + `relevance_score`. |
| Image / Video | `POST /v1/generations` | Single endpoint multiplexed by `model`. Image is sync by default (`image-gpt` also supports `mode: async`). Video requires `mode: sync | async`. |

Async generations return `{status: "submitted", task: {id}}` on submit; clients poll the same endpoint with `mode: async` + `input.taskId` and read `status: processing | succeeded | failed` plus `output.url` / `images[].url` (Aliyun OSS public URLs).

## Model Catalogue (2026-05-25)

| Capability | Models |
|---|---|
| Chat | `claude-opus-4-6`, `claude-sonnet-4-6`, `deepseek-v4-flash`, `deepseek-v4-pro`, `claude-sonnet-4-6:free`, `claude-opus-4-6:free`, `claude-opus-4-7:free`, `gpt-5.5-pro` |
| Responses | `gpt-5.5:free` |
| Embeddings | `jina-embeddings-v5-text-small` (default), `jina-embeddings-v5-text-nano`, `jina-embeddings-v5-omni-{small,nano}`, `jina-embeddings-{v4,v3}`, `jina-clip-{v2,v1}`, `jina-colbert-v2` |
| Rerank | `jina-reranker-v3` (flagship), `jina-reranker-m0`, `jina-reranker-v2-base-multilingual`, `jina-colbert-v2` |
| Image | `image-gemini-pro`, `image-gemini-flash`, `image-gpt` |
| Video | `video-seedance`, `video-happyhorse` |

> The model list is whatever the upstream page advertises on the day you read this. Re-fetch [the integration HTML](https://ai.mob-ai.cn/integration.html) (or run `GET /v1/models`) before pinning a model in a new service — entries get rotated.

## Smoke Test

```bash
export BASE_URL="https://ai.mob-ai.cn/api"
export MOB_AI_KEY="<mob-virtual-key>"

curl "$BASE_URL/v1/models" -H "Authorization: Bearer $MOB_AI_KEY"

curl "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $MOB_AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Return exactly: pong"}],"max_tokens":16,"stream":false}'
```

The full canonical curl + JavaScript + Python snippet pack is in [raw/2026-05-25-mob-ai-router-integration.md](../raw/2026-05-25-mob-ai-router-integration.md).

## Errors

| Status | Meaning | Typical Fix |
|---|---|---|
| 400 | Invalid JSON or missing required field | Check request schema and model name. |
| 401 | Missing / invalid virtual key | Resend with `Authorization: Bearer <mob-virtual-key>`. |
| 502 | Upstream/provider error | Retry; Jina + CC Dan paths go through a Cloudflare Worker upstream proxy. |
| 524 | Cloudflare upstream timeout | Provider was too slow — retry smaller, or switch to async mode for image / video. |

## Who Uses It

Already wired into several Lunaverse services (`https://ai.mob-ai.cn/api/v1` or its older `/v1` alias):

- [[concepts/codex-runtime-and-verification-layers]] — `LUNAVERSE_AGENT_BASE_URL=https://ai.mob-ai.cn/api/v1` for codex chat backend (provider `mob-ai`, models `deepseek-v4-flash`, `claude-sonnet-4-6`, etc.); L2 smoke test traverses this router end-to-end.
- [[concepts/dream-rec-dev-runbook]] — `MOB_AI_BASE_URL=https://ai.mob-ai.cn/v1` for dream-rec offline LLM workflows.
- [[concepts/dream-rec-component-2-llm-tagger]] — C2 tagger calls this gateway for novel tagging; described as "OpenAI-compatible" against the same `mob-ai gateway`.
- [[entities/assets-produce]] — Same gateway covers asset-pipeline LLM calls (prompt synthesis, etc.).

## Operational Notes

- **Virtual key, not provider key** — the whole point of this router is centralised quota / billing / provider rotation. Treat `mob-` keys as cross-provider creds and store them in the standard secret slots (`MOB_AI_KEY`, `LUNAVERSE_AGENT_API_KEY`, `MOB_AI_BASE_URL`, etc. — names differ per consumer).
- **`/v1` vs `/api/v1`** — both forms appear in existing wiki references. Treat `https://ai.mob-ai.cn/api` as the canonical base per the integration page; the bare `/v1` form is a historical alias still served.
- **Schema drift** — the upstream page lists `unsupported_fields` for the generations endpoints (`referenceImageUrls`, `refUrls`, `media`, `skipDownload`, `imageUrl`, `image_urls`, `video_urls`, `sourceVideoUrls`). Old client code carrying these fields will 400 — strip before sending.

## Related

- [raw/2026-05-25-mob-ai-router-integration.md](../raw/2026-05-25-mob-ai-router-integration.md) — verbatim mirror of the upstream integration HTML (frozen at 2026-05-25; refresh before relying on the model list).
- [[concepts/codex-runtime-and-verification-layers]] — primary consumer, with verified end-to-end L2 smoke through this router.
- [[concepts/dream-rec-component-2-llm-tagger]] — secondary consumer for novel tagging.
- [[entities/assets-produce]] — asset-pipeline LLM consumer.
