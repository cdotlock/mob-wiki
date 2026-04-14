"""Tests for WikiIndexer — FTS5 keyword search (embedding disabled)."""

import os
import textwrap

import pytest

from indexer import WikiIndexer

# ── Sample wiki pages used by fixtures ────────────────────────────────

SAN_SYSTEM_MD = textwrap.dedent("""\
    ---
    title: SAN System Overview
    tags: [sanity, health, game-mechanic]
    sources: [raw/2026-04-10-san-notes.md]
    created: 2026-04-10
    updated: 2026-04-12
    ---

    The SAN (Sanity) system tracks a character's mental health.
    When sanity drops below a threshold the character enters panic mode.

    ## Mechanics

    - Sanity ranges from 0 to 100
    - Events like combat and horror reduce sanity
    - Rest and safe zones restore sanity

    ## Related

    - [[concepts/stress-system]]
""")

REMIX_MD = textwrap.dedent("""\
    ---
    title: Remix Framework Guide
    tags: [web, framework, react]
    created: 2026-04-11
    updated: 2026-04-11
    ---

    Remix is a full-stack web framework built on React Router.
    It provides server-side rendering and nested routing.

    ## Key Features

    - Loader / action pattern
    - Nested routes with error boundaries
    - Progressive enhancement
""")


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_wiki(tmp_path):
    """Create a temporary wiki directory with sample pages."""
    wiki_dir = tmp_path / "wiki" / "concepts"
    wiki_dir.mkdir(parents=True)

    (tmp_path / "wiki" / "concepts" / "san-system.md").write_text(
        SAN_SYSTEM_MD, encoding="utf-8"
    )
    (tmp_path / "wiki" / "concepts" / "remix.md").write_text(
        REMIX_MD, encoding="utf-8"
    )

    # raw/ directory (empty but present)
    (tmp_path / "raw").mkdir()

    return tmp_path


@pytest.fixture()
def indexer(tmp_wiki):
    """WikiIndexer pointed at the temp wiki with embeddings disabled."""
    db_path = tmp_wiki / "db" / "wiki.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    idx = WikiIndexer(db_path=db_path, wiki_root=tmp_wiki)
    idx.build_index()
    yield idx
    idx.close()


# ── Tests ─────────────────────────────────────────────────────────────


def test_build_index(indexer):
    """build_index should find all markdown files under wiki/ and raw/."""
    # The fixture already called build_index; re-run to check the return value.
    stats = indexer.build_index()
    assert stats["pages_indexed"] == 2


def test_fts_search(indexer):
    """Searching 'sanity health' should surface the SAN system page."""
    results = indexer.search("sanity health")
    assert len(results) > 0
    paths = [r["path"] for r in results]
    assert any("san-system" in p for p in paths)


def test_fts_search_no_results(indexer):
    """Searching for a nonsense term should return an empty list."""
    results = indexer.search("xyznonexistent")
    assert results == []


def test_index_single_page(indexer):
    """Indexing a single page makes it searchable."""
    content = textwrap.dedent("""\
        ---
        title: New Concept
        tags: [alpha, beta]
        ---

        This page is about quantum entanglement in games.
    """)
    indexer.index_page("wiki/concepts/quantum.md", content)

    results = indexer.search("quantum entanglement")
    assert len(results) > 0
    assert results[0]["path"] == "wiki/concepts/quantum.md"


def test_remove_from_index(indexer):
    """After removing a page it should no longer appear in search."""
    # Confirm page is searchable first
    assert len(indexer.search("sanity")) > 0

    indexer.remove_page("wiki/concepts/san-system.md")

    results = indexer.search("sanity")
    paths = [r["path"] for r in results]
    assert "wiki/concepts/san-system.md" not in paths


def test_parse_frontmatter():
    """parse_frontmatter extracts title, tags, and body correctly."""
    meta, body = WikiIndexer.parse_frontmatter(SAN_SYSTEM_MD)

    assert meta["title"] == "SAN System Overview"
    assert "sanity" in meta["tags"]
    assert "health" in meta["tags"]
    assert "game-mechanic" in meta["tags"]
    assert "SAN (Sanity) system" in body
    # Frontmatter markers should not leak into body
    assert "---" not in body.split("\n")[0]
