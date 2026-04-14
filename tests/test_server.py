"""Tests for WikiServer — query tools (embedding disabled)."""

import textwrap

import pytest

from server import WikiServer

# -- Sample content --------------------------------------------------------

INDEX_MD = textwrap.dedent("""\
    ---
    title: Wiki Index
    updated: 2026-04-14
    ---

    # Mob-Wiki Index

    ## Concepts

    - [[concepts/san-system]] — SAN (sanity) health mechanic

    ## Entities

    (No pages yet)

    ## Syntheses

    (No pages yet)
""")

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

RAW_SOURCE_MD = textwrap.dedent("""\
    ---
    title: SAN Notes
    ---

    Raw design notes about the SAN system from the April 10 meeting.
    Players wanted a visible sanity meter on the HUD.
""")

LOG_MD = textwrap.dedent("""\
    ---
    title: Operation Log
    ---

    # Wiki Operation Log

    [2026-04-14 00:00] INIT: Wiki initialized
""")

# -- Fixtures --------------------------------------------------------------


@pytest.fixture()
def wiki_server(tmp_path):
    """WikiServer with a sample wiki structure, embeddings disabled."""
    # wiki/ directories
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "wiki" / "entities").mkdir(parents=True)
    (tmp_path / "wiki" / "syntheses").mkdir(parents=True)

    # wiki pages
    (tmp_path / "wiki" / "index.md").write_text(INDEX_MD, encoding="utf-8")
    (tmp_path / "wiki" / "log.md").write_text(LOG_MD, encoding="utf-8")
    (tmp_path / "wiki" / "concepts" / "san-system.md").write_text(
        SAN_SYSTEM_MD, encoding="utf-8"
    )

    # raw/ source
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "2026-04-10-san-notes.md").write_text(
        RAW_SOURCE_MD, encoding="utf-8"
    )

    # Database
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    db_path = db_dir / "wiki.db"

    srv = WikiServer(
        wiki_root=tmp_path,
        db_path=db_path,
        embedding_enabled=False,
    )
    srv.wiki_rebuild_index()
    yield srv
    srv.close()


# -- Tests: query tools ----------------------------------------------------


def test_wiki_list(wiki_server):
    """wiki_list returns the content of wiki/index.md."""
    result = wiki_server.wiki_list()
    assert "index" in result
    assert "Mob-Wiki Index" in result["index"]
    assert "san-system" in result["index"]


def test_wiki_read(wiki_server):
    """wiki_read returns page content and parsed frontmatter."""
    result = wiki_server.wiki_read("wiki/concepts/san-system.md")
    assert "content" in result
    assert "frontmatter" in result
    assert result["frontmatter"]["title"] == "SAN System Overview"
    assert "sanity" in result["frontmatter"]["tags"]
    assert "SAN (Sanity) system" in result["content"]


def test_wiki_read_raw(wiki_server):
    """wiki_read can read raw/ source files too."""
    result = wiki_server.wiki_read("raw/2026-04-10-san-notes.md")
    assert "content" in result
    assert "frontmatter" in result
    assert result["frontmatter"]["title"] == "SAN Notes"
    assert "sanity meter" in result["content"]


def test_wiki_read_not_found(wiki_server):
    """wiki_read returns error dict for missing files."""
    result = wiki_server.wiki_read("wiki/concepts/does-not-exist.md")
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_wiki_search(wiki_server):
    """Searching 'health mechanic' should find san-system."""
    result = wiki_server.wiki_search("health mechanic")
    assert "results" in result
    assert len(result["results"]) > 0
    paths = [r["path"] for r in result["results"]]
    assert any("san-system" in p for p in paths)


def test_wiki_search_empty(wiki_server):
    """Searching a nonsense term returns empty results list."""
    result = wiki_server.wiki_search("xyznonexistent")
    assert "results" in result
    assert result["results"] == []
