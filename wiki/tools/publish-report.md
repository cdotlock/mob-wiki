---
title: publish-report CLI
tags: [tool, deployment, mob-sandbox, static-site, html]
created: 2026-05-14
updated: 2026-05-14
---

`publish-report` is a one-shot CLI for deploying a local HTML/MD/static file or
directory to a public, browser-renderable URL. Default backend is mob-sandbox
`mob expose` (sslip.io-based public preview), chosen because it preserves the
local HTML rendering byte-for-byte and works in IP mode without DNS setup.

## Quick Usage

```bash
publish-report ./report.html                       # auto slug = "report"
publish-report ./report.html my-note               # explicit slug
publish-report ./docs/site/ project-x              # whole directory, served at /
```

Output URL example: `http://my-note.47.254.93.15.sslip.io:9876/report.html`
The URL is auto-copied to clipboard on macOS via `pbcopy`.

## How It Works

1. Locates a started Daytona sandbox via `mob ps` (or honors `PUBLISH_REPORT_SANDBOX` env var).
2. Reads `~/.config/mob/config.yaml` to extract the mob server URL and API key.
3. Uploads the local file/directory into the sandbox at `/home/daytona/published/<slug>/` by base64-encoding it and posting to the Daytona toolbox `POST /toolbox/<sandbox>/process/execute` endpoint (at `<server-host>:4000`).
4. Inside the sandbox, starts `python3 -m http.server <port> --directory /home/daytona/published/<slug>/`. The port is a deterministic 8000-8999 hash of the slug, so re-publishing the same slug reuses the same port (no orphan routes).
5. Calls `mob expose <sandbox> <port> <slug>` to register a sslip.io-based public route.

The exposed URL follows the pattern `http://<slug>.<server-ip>.sslip.io:9876/`. The `9876` port is the mob-server control daemon, which inspects the `Host` header and reverse-proxies traffic to the matching sandbox port. `sslip.io` is a public DNS service that turns any subdomain like `foo.1.2.3.4.sslip.io` into a record pointing back at `1.2.3.4` — no DNS configuration required, the trick that makes IP mode work without Traefik.

For single-file HTML uploads, the script also drops an `index.html` symlink so the bare URL (without a trailing filename) loads the page directly.

## Prerequisites

- `mob` CLI v0.1.3+ from `cdotlock/mob-sandbox` releases — earlier versions (v0.1.0 and below) reject `mob expose` in IP mode with a `requires domain mode` error. The fix landed 2026-05-05.
- `mob init` run once so `~/.config/mob/config.yaml` exists with the right `server`, `api_key`, `mode: ip` fields.
- At least one sandbox in `started` state (`mob ps` shows it).
- Python 3 installed inside the sandbox image (the stock `mob-sandbox:1.0` snapshot has it).

## Deprecated Backends

The script's earlier `--to=agent` and `--to=feishu` backends are gone. They are kept only as comments in the script header, with a clear ERROR message routing users to the new default if invoked:

- **`--to=agent`** — used to SSH-rsync to `root@agent.mob-ai.cn:/var/www/static_reports/<slug>/`. Stopped working after `agent.mob-ai.cn` was migrated behind Cloudflare orange-cloud proxy: Cloudflare's free tier only proxies HTTP ports (80/443/2052/2053/...), so SSH on 22 or 2222 is silently dropped during the banner exchange. Symptom: `kex_exchange_identification: Connection closed by remote host` from any port. Fix is server-side: cdotlock would need to add a grey-cloud subdomain (e.g. `ssh.mob-ai.cn` with a direct A record to the origin), enable Cloudflare Spectrum, or set up a Cloudflare Tunnel with `cloudflared access ssh`. Until then this backend is dead.
- **`--to=feishu`** — used `lark-cli drive +upload --as bot` to push a file to Feishu Drive with `link_share_entity: tenant_readable`. Two problems: (a) Feishu's preview pane treats `.html` as plain text source, not as a renderable page; (b) auto-rendering HTML → PDF via headless Chrome before upload produces a layout that does not match the local browser rendering. Neither meets the "page format identical to local" requirement. For non-HTML deliverables `lark-cli drive +upload --as bot` still works as a direct command.

## Why Not Other Routes

- **OSS public-read** (`mobai-file/nrbi/...`) — `oss-cn-shanghai` region's anti-phishing policy adds `Content-Disposition: attachment` + `x-oss-force-download: true` to every anonymous GET when the bucket host is the default `*.aliyuncs.com`. Signed URLs cannot override `response-content-disposition` for HTML in China region. Bypass would require a custom ICP-filed domain mapped to the bucket.
- **GitHub Pages** — works but requires the source repo to be public on the free plan. Internal technical reports probably do not belong in a public repo.
- **Agent-Forge `POST /api/oss/upload`** — works, but the returned URL is the same `mobai-file.oss-cn-shanghai.aliyuncs.com/...` with the same force-download header. Agent-Forge does not reverse-proxy OSS files through its own domain (`/api/public/*` returns 404).

## Failure Modes & Recovery

- `mob ps` empty → run `mob create` to make a new sandbox, or pass `PUBLISH_REPORT_SANDBOX=<id>` if there is an explicit one to target.
- `mob expose` fails with `route already exists` → the slug is in use. Pick a different one, or wait for the daemon's TTL to expire.
- HTTP server inside the sandbox refuses to bind → check `/tmp/pubrep-<slug>.log` inside the sandbox. Most common cause is the port already being held by an earlier python process; the script auto-kills and restarts.
- The URL loads but renders something stale → re-publishing replaces the file, but the python server caches nothing, so a hard browser reload (`Cmd+Shift+R`) should fetch fresh content.

## Related

- [[entities/mob-sandbox-ops]] — operational guide to the mob-sandbox platform (`mob` CLI, port exposure schemes A/B/C)
- [[entities/agent-forge]] — `agent.mob-ai.cn` is Agent-Forge's deployment, not a generic static host
