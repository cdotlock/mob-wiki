---
title: Wiki Schema
---

# Mob-Wiki Schema

This document defines the structural conventions for wiki pages. LLM agents
MUST follow these rules when creating or updating pages.

## Page Categories

| Category | Directory | Purpose |
|----------|-----------|---------|
| Concept | wiki/concepts/ | Abstract ideas, systems, patterns (e.g., SAN system, Remix flow) |
| Entity | wiki/entities/ | Concrete things: products, services, people, repos |
| Synthesis | wiki/syntheses/ | Cross-cutting analyses, comparisons, decision records |

## Frontmatter (Required)

Every wiki page MUST have YAML frontmatter:

    ---
    title: Human-Readable Page Title
    tags: [tag1, tag2]
    sources: [raw/YYYY-MM-DD-source.md]
    created: YYYY-MM-DD
    updated: YYYY-MM-DD
    ---

- `title`: concise, descriptive
- `tags`: 1-5 lowercase tags for categorization
- `sources`: list of raw/ files this page draws from (can be empty for syntheses)
- `created` / `updated`: ISO dates

## Page Structure

1. **Summary** (2-3 sentences) — what this page is about, immediately after frontmatter
2. **Body** — detailed content, use ## headings to organize
3. **Cross-references** — use `[[page-name]]` wikilinks to link related pages
4. **Sources** — cite raw documents with `[source](../raw/filename.md)`

## Naming Conventions

- Filenames: lowercase, hyphens, no spaces. e.g., `san-system.md`
- One concept/entity per page — if a page grows beyond ~500 words, split it
- Wikilinks: `[[concepts/san-system]]` (path relative to wiki/, no .md extension)

## index.md Maintenance

After any page create/update, update `wiki/index.md`:
- Add new pages under the correct category heading
- Format: `- [[category/page-name]] — one-line description`
- Keep entries sorted alphabetically within each category

## log.md Format

Append one line per operation:
`[YYYY-MM-DD HH:MM] ACTION: description`

Actions: INGEST, CREATE, UPDATE, LINT, REBUILD
