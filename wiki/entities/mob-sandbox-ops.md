---
title: Mob Sandbox Ops
tags: [ops, sandbox, daytona, openhands, vultr]
sources: []
created: 2026-04-30
updated: 2026-05-03
---

Mob Sandbox is a self-hosted AI coding sandbox platform built around Daytona, Traefik, OpenHands, and a pair of Go CLIs. It gives operators a way to start/stop the backing VPS, create isolated Daytona sandboxes, connect through SSH or Claude Code, expose preview URLs, and onboard additional operators without sharing cloud provider API keys.

## Repository Identity

| Field | Value |
|---|---|
| Repository path | `/Users/Clock/mob-sandbox` |
| Remote | `https://github.com/cdotlock/mob-sandbox.git` |
| Main branch | `main` |
| Server CLI | `cmd/mob-server` |
| Client CLI | `cmd/mob` |
| Server stack | Daytona, Traefik, OpenHands, Guardian |
| Power-control stack | Cloudflare Worker + Vultr API + SSH-signature auth |
| Domain mode | Supports DNS, TLS, preview URLs, and permanent subdomain routes |
| IP mode | Supports bare-IP operation with SSH port forwarding |

The repository was created from an April 2026 self-hosted coding-agent PoC. The May 2026 changes made the client experience more usable: remote Claude Code sessions, automatic sandbox start before connection, an interactive TUI, transient readiness retries, and OpenHands default port `3100`.

## Security Model

Do not store cloud provider credentials or LLM tokens in markdown. Early runbook history contained plaintext Vultr and Porkbun keys; the repository's current runbook explicitly says those keys must be rotated and replaced through local `.env` values. The wiki should only document variable names and command shapes.

Required local secret fields:

```text
VULTR_API_KEY=<your-vultr-api-key>
PORKBUN_API_KEY=<your-porkbun-api-key>
PORKBUN_SECRET_KEY=<your-porkbun-secret-key>
VM_ID=<vultr-instance-uuid>
VM_IP=<vps-public-ip>
DOMAIN=<sandbox-domain>
VULTR_SSH_KEY_ID=<uploaded-vultr-ssh-key-id>
```

Load them with:

```bash
set -a && source .env && set +a
```

The operator's private SSH key stays local. The default examples use `~/.ssh/poc_ed25519`, but the platform is designed so each operator can use their own keypair.

## Architecture

```text
developer laptop
  mob CLI
    -> HTTPS control API
    -> Daytona API
    -> SSH gateway / port forward
    -> Cloudflare Worker power API

Ubuntu server
  mob-server daemon
    -> Daytona services
    -> Traefik TLS/router
    -> OpenHands
    -> Guardian health/repair loop
```

The server stack is deployed by `mob-server init`. The client stack is configured by `mob init`. After client configuration, running `mob` opens the Bubble Tea dashboard by default.

## Server CLI

`mob-server` runs on the VPS and manages deployment, server status, Daytona API keys, operator SSH keys, and daemon lifecycle.

| Command | Purpose |
|---|---|
| `mob-server init --domain example.com --dns-provider porkbun --dns-token xxx --llm-key sk-xxx` | Initialize the server in domain mode with DNS and LLM configuration. |
| `mob-server init --ssh-host <host> --ssh-key <path>` | Initialize or bootstrap against a specific SSH host/key flow. |
| `mob-server status` | Print server/platform status. |
| `mob-server key create <name>` | Create a Daytona API key. |
| `mob-server key list` | List Daytona API keys. |
| `mob-server key revoke <name>` | Revoke a Daytona API key. |
| `mob-server operator add <name> -f <pubkey>` | Add an SSH operator public key. |
| `mob-server operator list` | List operators. |
| `mob-server operator revoke <name>` | Revoke an operator. |
| `mob-server operator worker-config` | Print Cloudflare Worker authorization JSON for configured operators. |
| `mob-server daemon` | Start the long-running server daemon. |

The server embeds compose templates and a sandbox Dockerfile through Go `embed`, so packaged binaries can deploy without separately copying all template files.

## Client CLI

`mob` runs on the developer laptop. With no subcommand it opens the interactive TUI.

| Command | Purpose |
|---|---|
| `mob` | Open the interactive dashboard. |
| `mob tui` | Explicitly open the dashboard. |
| `mob init` | Configure client connection, API key, SSH settings, OpenHands URL, and control URL. |
| `mob create` | Create a new Daytona sandbox. |
| `mob ps` | List sandboxes. |
| `mob ssh [id]` | SSH into a sandbox; if no ID is given, create or choose one. |
| `mob claude [id]` | Start Claude Code inside a sandbox. |
| `mob rm <id>` | Delete a sandbox. |
| `mob forward <id> <port>` | Forward a sandbox port to localhost over SSH. |
| `mob url <id> <port>` | Generate a temporary preview URL in domain mode. |
| `mob expose <id> <port> [name]` | Create a durable subdomain route in domain mode. |
| `mob openhands` | Open OpenHands in the browser. |
| `mob power init` | Configure power-control Worker URL and operator identity. |
| `mob power start` | Start the VPS through the Worker. |
| `mob power stop` | Stop the VPS through the Worker. |
| `mob power reboot` | Reboot the VPS through the Worker. |
| `mob power status` | Query VPS power status through the Worker. |

The TUI supports sandbox refresh, sandbox creation, SSH/Claude Code entry, localhost tunnel management, preview URL generation, permanent route creation, deletion, OpenHands launch, and VPS power actions from one dashboard. SSH and Claude Code temporarily take over the terminal; exiting the remote session returns to the dashboard.

## OpenHands Port Convention

OpenHands now defaults to port `3100`. The config constant is:

```text
DefaultOpenHandsPort = 3100
```

Client initialization sets the OpenHands URL differently by mode:

| Mode | OpenHands URL |
|---|---|
| Domain mode | `https://openhands.<domain>` |
| IP mode | `http://<host>:3100` by default |

The May 2026 history includes a commit titled `Default OpenHands to port 3100`, updating Makefile defaults, config defaults, and CLI design docs.

## Sandbox Runtime

Each sandbox image includes:

| Tool | Purpose |
|---|---|
| Claude Code 2.1.123 | Primary coding-agent runtime inside the sandbox. |
| Python 3.11 | Python development and scripting. |
| Node.js 22 | JavaScript/TypeScript development. |
| ttyd | Web terminal support. |
| Git, curl, wget | Baseline development utilities. |

Claude Code credentials should be injected at sandbox creation time or through root-only runtime files. Do not bake LLM auth tokens into images, registries, or git-tracked files.

## Port Exposure

| Exposure mode | Command | Works in | Use case |
|---|---|---|---|
| SSH tunnel | `mob forward <id> <port>` | Domain and IP mode | Private local preview. |
| Preview URL | `mob url <id> <port>` | Domain mode | Temporary shareable preview. |
| Permanent subdomain | `mob expose <id> <port> [name]` | Domain mode | Long-running public route. |

Traefik handles the domain-mode routing. The May 2026 fix for malformed upstream URLs in `mob expose` corrected control-server route generation.

## Power Control

Direct operators should prefer `mob power` instead of holding the Vultr API key. The Cloudflare Worker receives signed requests from an operator key, verifies the operator against `AUTHORIZED_PUBKEYS`, and then calls the Vultr API.

Operator onboarding flow:

1. Operator creates a local keypair with `ssh-keygen -t ed25519`.
2. Operator sends the public key to an admin.
3. Admin runs `mob-server operator add <name> -f <name>.pub`.
4. Admin copies the generated JSON into `infra/power-worker/wrangler.toml` under `AUTHORIZED_PUBKEYS`.
5. Admin deploys the Worker from `infra/power-worker` with `npx wrangler deploy`.
6. Operator runs `mob power init`.
7. Operator tests `mob power status`.

Revocation requires both `mob-server operator revoke <name>` and removing that operator from Worker config before redeploying the Worker.

## Daytona Operations Lessons

The 2026-05-02 ops notes record several reusable Daytona lessons:

| Area | Lesson |
|---|---|
| Health order | Debug from the outside inward: SSH, Docker, Daytona health, `mob ps`, then create/delete sandbox. |
| Snapshot endpoint | Daytona v0.171 uses `POST /api/snapshots` and `GET /api/snapshots/{id}`; older singular paths 404. |
| Snapshot name | Use `mob-sandbox:1.0` so the client can create sandboxes by snapshot name. |
| Quotas | Fresh organizations may have per-sandbox limits at zero; update organization and region quota rows. |
| API key schema | Current Daytona keys need `keyHash`, `keyPrefix`, and `keySuffix`. Cleartext keys stay local. |
| API restart | Restart `daytona-api` after fixing quota rows so checks reload. |

## DNS And TLS Lessons

| Area | Lesson |
|---|---|
| Porkbun DNS-01 | Traefik v3.3 with Porkbun DNS-01 can fail ACME record creation due provider response decoding. |
| HTTP-01 | Simpler for explicit hosts such as `daytona.<domain>` and `openhands.<domain>`. |
| Wildcards | HTTP-01 does not issue wildcard certificates; wildcard previews need DNS-01 or explicit host routing. |
| HostRegexp YAML | Quote HostRegexp rules containing backslashes with single quotes. |
| DNS deletion | Do not delete DNS records unless the operator explicitly approves. Prefer adding/changing routes first. |

Required domain records in Porkbun for domain mode:

```bash
pb_create ""              "${VM_IP}"   # ${DOMAIN}
pb_create "*"             "${VM_IP}"   # *.${DOMAIN}
pb_create "daytona"       "${VM_IP}"   # daytona.${DOMAIN}
pb_create "openhands"     "${VM_IP}"   # openhands.${DOMAIN}
pb_create "*.proxy"       "${VM_IP}"   # *.proxy.${DOMAIN}
pb_create "*.node.proxy"  "${VM_IP}"   # *.node.proxy.${DOMAIN}
```

Porkbun wildcard syntax is `*.node.proxy`, not `node.proxy.*`.

## SSH And Claude Code Lessons

| Area | Lesson |
|---|---|
| KEX option | Vultr SSH examples use `-o KexAlgorithms=curve25519-sha256`; keep it in scripts that require it. |
| Claude location | Launch Claude Code inside the Daytona sandbox, not locally. |
| Environment injection | `mob create`, `mob ssh`, and `mob claude` inject configured Claude Code env into new sandboxes. |
| PATH safety | Sandbox env injection can override image PATH; keep Node and Claude reachable through `/usr/local/bin` symlinks. |
| Claude command | `mob claude` should call `/usr/local/bin/claude` to avoid PATH surprises. |
| Terminal raw mode | TUI and remote sessions need raw mode and terminal size propagation for arrow keys and resize behavior. |
| Token diagnostics | Verify token presence by length or prefix-only checks; never print full auth tokens. |

## Verification

Baseline repository verification:

```bash
go test ./...
```

Platform smoke verification:

```bash
./bin/mob ps
./bin/mob create
./bin/mob claude <sandbox-id>
```

Inside a sandbox:

```bash
/usr/local/bin/claude --version
printf '%s\n' "$ANTHROPIC_BASE_URL"
printf '%s\n' "${#ANTHROPIC_AUTH_TOKEN}"
```

For DNS:

```bash
dig +short daytona.${DOMAIN} @8.8.8.8
dig +short openhands.${DOMAIN} @8.8.8.8
dig +short test.node.proxy.${DOMAIN} @8.8.8.8
```

## Relationship To Other Pages

Mob Sandbox provides the remote development substrate for agents that work on [[entities/lunaverse-backend]], [[entities/dramatizer-ls]], [[entities/video-agent-claude-wangbo]], and other Lunaverse repositories. It is operational infrastructure, not content production logic.

## Sources

This page was reconstructed from the local repository at `/Users/Clock/mob-sandbox`, especially:

- `README.md`
- `docs/ops-vultr-porkbun-runbook.md`
- `docs/operator-onboarding.md`
- `docs/ops-lessons-2026-05-02.md`
- `docs/mob-cli-design-spec.md`
- Git history from 2026-04-30 through 2026-05-03
