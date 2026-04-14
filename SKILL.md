---
name: mob-wiki
description: Team knowledge base — ingest documents, query knowledge, maintain wiki health
---

# Mob-Wiki Skill

You are operating the team's shared knowledge base (repo: cdotlock/mob-wiki).
The wiki uses MCP tools for all operations. Files live in ~/mob-wiki/.

## When This Skill Activates

- User says "ingest", "add to wiki", "update wiki", "入库", "wiki" + any action verb
- User asks about project architecture, design decisions, product logic, history
- User produces a PRD, design doc, or technical spec
- User says "lint wiki", "check wiki", "wiki health"

## Architecture

Three layers:
- `raw/` — immutable source documents (never modify these)
- `wiki/` — LLM-compiled knowledge pages (you manage these)
- `schema.md` — structural rules (read this before writing pages)

## Workflow: Ingest

When a new document needs to enter the knowledge base:

1. Sync: run `git pull` in ~/mob-wiki/
2. Place the source file in `raw/` with naming `YYYY-MM-DD-<slug>.md`
3. Call `wiki_ingest` with the source path
4. Read the returned source content and current index
5. Decide which wiki pages to create or update:
   - New concept/entity/synthesis? → `wiki_create_page`
   - Existing page needs update? → `wiki_update_page`
6. Update `wiki/index.md` with any new/changed pages
7. Append to `wiki/log.md`: `[date time] INGEST: <source-name>`
8. Commit and push:
   ```
   git add .
   git commit -m "wiki: ingest <source-name>"
   git push
   ```

## Workflow: Query

When asked a question about the project:

1. Sync: run `git pull` in ~/mob-wiki/
2. Call `wiki_list` to see the table of contents
3. Call `wiki_search` with a semantic query
4. Call `wiki_read` for the top relevant pages
5. Answer the question, citing wiki page paths
6. If your answer contains new insight worth keeping:
   - Offer to create a synthesis page

## Workflow: Lint

When asked to check wiki health, or periodically:

1. Sync: run `git pull` in ~/mob-wiki/
2. Call `wiki_lint`
3. Review each issue:
   - Broken links → fix or remove the link
   - Orphan pages → add to index.md or link from related pages
   - Stale pages → re-read the source, update the page
   - Missing frontmatter → add the missing fields
4. Commit fixes: `git commit -m "wiki: lint fix" && git push`

## Page Writing Rules

Read `schema.md` for full details. Key rules:
- Always include YAML frontmatter (title, tags, sources, created, updated)
- Lead with a 2-3 sentence summary
- Use `[[wikilinks]]` for cross-references between pages
- Cite sources with `[source](../raw/filename.md)` links
- One concept/entity per page
- Keep pages under ~500 words; split if longer
