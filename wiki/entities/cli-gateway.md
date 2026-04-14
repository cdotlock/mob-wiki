---
title: CLI Gateway
tags: [microservice, http, cli, cloud, deployment]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

Lightweight HTTP microservice deployed alongside each Moonshort platform service. Enables remote CLI command execution while preserving the full CLI experience (progressive discovery, help caching, self-correction).

## Deployments

| Service | Implementation | Port | Commands |
|---------|---------------|------|----------|
| [[entities/dramatizer]] | Go (`dram gateway`) | 9001 | `dram` |
| [[entities/agent-forge]] | TypeScript (`cli-gateway/server.ts`) | 9001 | `forge-eval` |
| [[entities/moonshort-backend]] | TypeScript (`cli-gateway/server.ts`) | 9002 | `noval` |
| [[entities/moonshort-client]] | TypeScript (`cli-gateway/server.ts`) | 9003 | `play`, `test` |

## Protocol

See [[concepts/cli-gateway-protocol]] for the full HTTP API specification.

## Security

- Bearer token auth (`CLI_GATEWAY_KEY` env var)
- Command allowlist (only configured tools)
- No shell expansion (`spawn` direct, no `sh -c`)
- Argument injection filtering (rejects `;`, `|`, `` ` ``, `$()`, `&&`, `||`)
- Timeout enforcement with process kill

## Relationship to mobai-agent

[[entities/mobai-agent]]'s `cli_run` tool checks `config.yaml` → `cli.gateways` before local execution. If a command matches a gateway, it routes transparently via HTTP. The agent is completely unaware of remote vs local execution.

## Related

- [[concepts/cli-gateway-protocol]]
- [[concepts/four-layer-philosophy]]
- [[syntheses/cloud-deployment-architecture]]

## Sources

- [Design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
