---
name: mob-ai-router-integration
description: Mob AI Router public HTTP API integration reference — base URL, auth, endpoints, model catalogue, snippets
source_url: https://ai.mob-ai.cn/integration.html
fetched: 2026-05-28
upstream_last_modified: 2026-05-25
---

# Mob AI Router Integration Reference

Verbatim text extraction of https://ai.mob-ai.cn/integration.html (HTML stripped). The upstream page declares itself the canonical external integration guide and is optimized for LLM/source-code reading.

## Machine-Readable Summary

```json
{
  "service": "mob-ai-router",
  "base_url": "https://ai.mob-ai.cn/api",
  "auth": {
    "type": "bearer",
    "header": "Authorization: Bearer <mob-virtual-key>"
  },
  "endpoints": {
    "models": "GET /v1/models",
    "chat_completions": "POST /v1/chat/completions",
    "responses": "POST /v1/responses",
    "embeddings": "POST /v1/embeddings",
    "rerank": "POST /v1/rerank",
    "generations": "POST /v1/generations"
  },
  "text_models": [
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "claude-sonnet-4-6:free",
    "claude-opus-4-6:free",
    "claude-opus-4-7:free",
    "gpt-5.5:free",
    "gpt-5.5-pro"
  ],
  "embedding_models": [
    "jina-embeddings-v5-text-small",
    "jina-embeddings-v5-text-nano",
    "jina-embeddings-v5-omni-small",
    "jina-embeddings-v5-omni-nano",
    "jina-embeddings-v4",
    "jina-embeddings-v3",
    "jina-clip-v2",
    "jina-clip-v1",
    "jina-colbert-v2"
  ],
  "rerank_models": [
    "jina-reranker-v3",
    "jina-reranker-m0",
    "jina-reranker-v2-base-multilingual",
    "jina-colbert-v2"
  ],
  "image_models": ["image-gemini-pro", "image-gemini-flash", "image-gpt"],
  "video_models": ["video-seedance", "video-happyhorse"]
}
```

## Auth

All public API calls use the same Mob AI `mob-`-prefixed virtual key. Do not send provider keys to this router.

```
Authorization: Bearer <mob-virtual-key>
Content-Type: application/json
```

## Capability → Model → Endpoint

| Capability | Models | Endpoint |
|---|---|---|
| Chat | `claude-opus-4-6`, `claude-sonnet-4-6`, `deepseek-v4-flash`, `deepseek-v4-pro`, `claude-sonnet-4-6:free`, `claude-opus-4-6:free`, `claude-opus-4-7:free`, `gpt-5.5-pro` | `POST /v1/chat/completions` |
| Responses | `gpt-5.5:free` | `POST /v1/responses` |
| Embeddings | `jina-embeddings-v5-text-small`, `jina-embeddings-v5-text-nano`, `jina-embeddings-v5-omni-small`, `jina-embeddings-v5-omni-nano`, `jina-embeddings-v4`, `jina-embeddings-v3`, `jina-clip-v2`, `jina-clip-v1`, `jina-colbert-v2` | `POST /v1/embeddings` |
| Rerank | `jina-reranker-v3`, `jina-reranker-m0`, `jina-reranker-v2-base-multilingual`, `jina-colbert-v2` | `POST /v1/rerank` |
| Image | `image-gemini-pro`, `image-gemini-flash`, `image-gpt` | `POST /v1/generations` |
| Video | `video-seedance`, `video-happyhorse` | `POST /v1/generations` |

## Chat Completions

OpenAI-compatible. Use `max_tokens` for most models. `gpt-5.5-pro` also accepts `max_completion_tokens`.

```bash
curl https://ai.mob-ai.cn/api/v1/chat/completions \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "Return exactly: pong"}],
    "max_tokens": 16,
    "stream": false
  }'
```

```bash
curl https://ai.mob-ai.cn/api/v1/chat/completions \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5.5-pro",
    "messages": [{"role": "user", "content": "Return exactly: pong"}],
    "max_completion_tokens": 16,
    "stream": false
  }'
```

## Responses

Use this endpoint for `gpt-5.5:free`.

```bash
curl https://ai.mob-ai.cn/api/v1/responses \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5.5:free",
    "input": "Return exactly: pong"
  }'
```

## Embeddings

Jina embedding route. Response contains `data[0].embedding`, a numeric vector.

```bash
curl https://ai.mob-ai.cn/api/v1/embeddings \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jina-embeddings-v5-text-small",
    "task": "retrieval.query",
    "input": ["hello world"]
  }'
```

Schema:

```json
{
  "required": ["model", "input"],
  "model": "jina-embeddings-v5-text-small | jina-embeddings-v5-text-nano | jina-embeddings-v5-omni-small | jina-embeddings-v5-omni-nano | jina-embeddings-v4 | jina-embeddings-v3 | jina-clip-v2 | jina-clip-v1 | jina-colbert-v2",
  "input": "string | string[] | image/audio/video/PDF object for multimodal models",
  "passthrough_fields": ["task", "dimensions", "late_chunking"]
}
```

## Rerank

Jina rerank route. Response contains a ranked results array with `index` and `relevance_score`.

```bash
curl https://ai.mob-ai.cn/api/v1/rerank \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jina-reranker-v3",
    "query": "what is mob ai",
    "documents": ["Mob AI is an AI routing service.", "This document is unrelated."],
    "top_n": 1,
    "return_documents": true
  }'
```

Schema:

```json
{
  "required": ["model", "query", "documents"],
  "model": "jina-reranker-v3 | jina-reranker-m0 | jina-reranker-v2-base-multilingual | jina-colbert-v2",
  "query": "string",
  "documents": "string[] | object[]",
  "optional": ["top_n", "return_documents"]
}
```

## Image / Video Generations

### Image (sync default; `image-gpt` also supports async)

```bash
curl https://ai.mob-ai.cn/api/v1/generations \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "image-gpt",
    "input": {"prompt": "a small red robot"}
  }'
```

Schema:

```json
{
  "required": ["model", "input.prompt"],
  "model": "image-gpt | image-gemini-pro | image-gemini-flash",
  "input": {
    "prompt": "string",
    "references": [{"type": "image", "url": "https://example.com/image.png"}]
  },
  "mode": "optional for image-gpt only: sync | async",
  "unsupported_fields": ["referenceImageUrls", "refUrls", "media", "skipDownload"]
}
```

GPT Image async submit:

```bash
curl https://ai.mob-ai.cn/api/v1/generations \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "image-gpt",
    "mode": "async",
    "input": {
      "prompt": "your sprite prompt",
      "references": [
        {"type": "image", "url": "https://example.com/ref1.png"},
        {"type": "image", "url": "https://example.com/ref2.png"}
      ]
    }
  }'
```

Response: `{"status": "submitted", "task": {"id": "task-id"}, "result": {"taskId": "task-id"}, "provider": "gpt-image2"}`.

GPT Image async query:

```bash
curl https://ai.mob-ai.cn/api/v1/generations \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "image-gpt",
    "mode": "async",
    "input": {"taskId": "task-id"}
  }'
```

Response: `status: processing | succeeded | failed`, with `output.url` and `images[].url` pointing to `https://bucket.oss-region.aliyuncs.com/public/image/file.png` once finished.

### Video (requires `mode: sync | async`)

```bash
curl https://ai.mob-ai.cn/api/v1/generations \
  -H "Authorization: Bearer <mob-virtual-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "video-seedance",
    "mode": "async",
    "input": {
      "prompt": "animate this image",
      "references": [{"type": "image", "url": "https://example.com/start.png"}],
      "duration": 5,
      "ratio": "16:9"
    }
  }'
```

Schema:

```json
{
  "submit_required": ["model", "mode", "input.prompt"],
  "query_required": ["model", "mode", "input.taskId"],
  "model": "video-seedance | video-happyhorse",
  "mode": "sync | async",
  "input": {
    "prompt": "string",
    "taskId": "string, for async query",
    "references": [{"type": "image | video", "url": "https://example.com/media"}],
    "duration": "positive number",
    "frames": "positive number",
    "ratio": "string",
    "resolution": "string",
    "model": "string"
  },
  "unsupported_fields": ["media", "referenceImageUrls", "imageUrl", "image_urls", "video_urls", "sourceVideoUrls"]
}
```

## Errors

| Status | Meaning | Typical Fix |
|---|---|---|
| 400 | Invalid JSON or missing required field | Check request schema and model name. |
| 401 | Missing or invalid virtual key | Use `Authorization: Bearer <mob-virtual-key>`. |
| 502 | Upstream/provider error | Retry or check provider status. For Jina / CC Dan this router uses a Cloudflare Worker upstream proxy. |
| 524 | Cloudflare upstream timeout | Provider was too slow; retry with a smaller request. |

## Smoke Tests

```bash
export BASE_URL="https://ai.mob-ai.cn/api"
export MOB_AI_KEY="<mob-virtual-key>"

curl "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $MOB_AI_KEY"

curl "$BASE_URL/v1/embeddings" \
  -H "Authorization: Bearer $MOB_AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"jina-embeddings-v5-text-small","task":"retrieval.query","input":["hello world"]}'

curl "$BASE_URL/v1/rerank" \
  -H "Authorization: Bearer $MOB_AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"jina-reranker-v3","query":"hello","documents":["hello world","goodbye"],"top_n":1}'
```

## Copy-Paste Client Snippets

### JavaScript

```javascript
const BASE_URL = "https://ai.mob-ai.cn/api";
const key = process.env.MOB_AI_KEY;

async function mobAI(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${key}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

const chat = await mobAI("/v1/chat/completions", {
  model: "deepseek-v4-flash",
  messages: [{ role: "user", content: "Return exactly: pong" }],
  max_tokens: 16,
  stream: false
});

const embedding = await mobAI("/v1/embeddings", {
  model: "jina-embeddings-v5-text-small",
  task: "retrieval.query",
  input: ["hello world"]
});

const rerank = await mobAI("/v1/rerank", {
  model: "jina-reranker-v3",
  query: "hello",
  documents: ["hello world", "goodbye"],
  top_n: 1
});
```

### Python

```python
import os
import requests

BASE_URL = "https://ai.mob-ai.cn/api"
HEADERS = {
    "Authorization": f"Bearer {os.environ['MOB_AI_KEY']}",
    "Content-Type": "application/json",
}

def mob_ai(path, payload):
    r = requests.post(BASE_URL + path, headers=HEADERS, json=payload, timeout=900)
    r.raise_for_status()
    return r.json()

chat = mob_ai("/v1/chat/completions", {
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "Return exactly: pong"}],
    "max_tokens": 16,
    "stream": False,
})

embedding = mob_ai("/v1/embeddings", {
    "model": "jina-embeddings-v5-text-small",
    "task": "retrieval.query",
    "input": ["hello world"],
})

rerank = mob_ai("/v1/rerank", {
    "model": "jina-reranker-v3",
    "query": "hello",
    "documents": ["hello world", "goodbye"],
    "top_n": 1,
})
```
