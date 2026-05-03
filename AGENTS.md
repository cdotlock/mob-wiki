# Mob-Wiki Repository Rules

This is the team shared knowledge base. All wiki operations go through the MCP tools.

## File Permissions
- `raw/` — read only. Never modify source documents.
- `wiki/` — read/write. You are responsible for maintaining these pages.
- `schema.md` — read only. Follow its conventions when writing pages.
- `db/` — managed by the server. Do not touch directly.

## Before Writing
Always `git pull` before any write operation to avoid merge conflicts.

## After Writing
Always `git add . && git commit && git push` after wiki changes.

## Commit Messages
- `wiki: ingest <source>` — new source ingested
- `wiki: update <page>` — existing page updated
- `wiki: lint fix` — automated lint fixes
- `chore: <desc>` — tooling/server changes
