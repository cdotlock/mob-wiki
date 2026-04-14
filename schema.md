---
title: Wiki Schema
---

# Mob-Wiki Schema

This document defines the structural conventions for wiki pages. LLM agents
MUST follow these rules when creating or updating pages.

## Documentation Quality Standard

**This is a non-negotiable rule.** All wiki pages MUST be written as complete, reference-grade documentation. A reader should be able to understand the system thoroughly from the wiki alone, without needing to read source code.

### Prohibited
- Abbreviated or summary-style pages ("缩写文档")
- Bullet-point-only pages with no explanatory prose
- Placeholder sections ("TBD", "TODO", "etc.", "and more")
- Omitting details because they seem "obvious"

### Required
- Every tool, command, endpoint, parameter, and configuration option must be listed explicitly — no "etc."
- Technical concepts must be explained with enough context that a new team member can understand them
- Architecture sections must describe every module with its purpose, inputs, outputs, and relationships
- Protocol sections must include full request/response schemas with field-level descriptions
- CLI sections must list every command, every flag, and every option

### Product Docs vs Technical Docs

When a page covers both user-facing and implementation concerns, split into clearly labeled sections:

- **Product sections** focus on what, why, and how to use: features, workflows, configuration, usage examples
- **Technical sections** focus on how it works internally: architecture, data flow, code modules, schemas, protocols

Both types require the same level of completeness. Product docs are not permission to be vague. Technical docs are not permission to skip user context.

### Length Guideline

A well-written entity page for a major service (e.g., mobai-agent, Dramatizer) should be 300-600 lines. A concept page explaining a core architectural pattern should be 150-400 lines. A synthesis page analyzing cross-cutting concerns should be 200-500 lines. If a page is under 100 lines, it is almost certainly too brief.

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
