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

GAME_DESIGN_MD = textwrap.dedent("""\
    ---
    title: Game Design Notes
    ---

    # Game Design

    Core loop and mechanics for the mob-wiki game prototype.
    Players explore a world where SAN (sanity) is the primary resource.
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
    (tmp_path / "raw" / "2026-04-01-game-design.md").write_text(
        GAME_DESIGN_MD, encoding="utf-8"
    )

    # Database
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    db_path = db_dir / "wiki.db"

    srv = WikiServer(wiki_root=tmp_path, db_path=db_path)
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


# -- Tests: ingest and maintenance tools ------------------------------------


def test_wiki_ingest(wiki_server):
    """wiki_ingest should return source content and current index."""
    result = wiki_server.wiki_ingest("raw/2026-04-01-game-design.md")
    assert "error" not in result
    assert "Game Design" in result["source_content"]
    assert "Mob-Wiki Index" in result["current_index"]
    assert "instructions" in result


def test_wiki_ingest_not_found(wiki_server):
    """wiki_ingest should error for missing source."""
    result = wiki_server.wiki_ingest("raw/nonexistent.md")
    assert "error" in result


def test_wiki_create_page(wiki_server, tmp_path):
    """wiki_create_page should create a new page and index it."""
    content = (
        "---\ntitle: Test Page\ntags: [test]\n"
        "created: 2026-04-14\nupdated: 2026-04-14\n---\n\n"
        "This is a test page about testing.\n"
    )
    result = wiki_server.wiki_create_page("wiki/concepts/test-page.md", content)
    assert result.get("created") == "wiki/concepts/test-page.md"
    assert result.get("indexed") is True
    # Verify file exists
    assert (tmp_path / "wiki" / "concepts" / "test-page.md").exists()
    # Verify searchable
    search = wiki_server.wiki_search("testing")
    assert any("test-page" in r["path"] for r in search["results"])


def test_wiki_create_page_already_exists(wiki_server):
    """wiki_create_page should error if page exists."""
    result = wiki_server.wiki_create_page("wiki/concepts/san-system.md", "---\ntitle: X\n---\n")
    assert "error" in result


def test_wiki_create_page_no_frontmatter(wiki_server):
    """wiki_create_page should require frontmatter with title."""
    result = wiki_server.wiki_create_page("wiki/concepts/bad.md", "No frontmatter here")
    assert "error" in result


def test_wiki_update_page(wiki_server, tmp_path):
    """wiki_update_page should overwrite content and re-index."""
    new_content = (
        "---\ntitle: SAN System (Updated)\ntags: [game, health, updated]\n"
        "sources: [raw/2026-04-01-game-design.md]\n"
        "created: 2026-04-01\nupdated: 2026-04-14\n---\n\n"
        "Updated SAN system description with new mechanics.\n"
    )
    result = wiki_server.wiki_update_page("wiki/concepts/san-system.md", new_content)
    assert result.get("updated") == "wiki/concepts/san-system.md"
    read = wiki_server.wiki_read("wiki/concepts/san-system.md")
    assert "Updated" in read["content"]


def test_wiki_update_page_not_found(wiki_server):
    """wiki_update_page should error for missing page."""
    result = wiki_server.wiki_update_page("wiki/concepts/nonexistent.md", "---\ntitle: X\n---\n")
    assert "error" in result


def test_wiki_lint(wiki_server):
    """wiki_lint should detect issues."""
    result = wiki_server.wiki_lint()
    assert "issues" in result
    assert isinstance(result["issues"], list)


def test_wiki_rebuild_index(wiki_server):
    """wiki_rebuild_index should return counts."""
    result = wiki_server.wiki_rebuild_index()
    assert result["pages_indexed"] >= 2


# -- Tests: HTTP viewer smoke tests -----------------------------------------

import pytest

try:
    from starlette.testclient import TestClient
    from server import _http_app

    _HTTP_AVAILABLE = _http_app is not None
except ImportError:
    _HTTP_AVAILABLE = False


@pytest.mark.skipif(not _HTTP_AVAILABLE, reason="starlette/http_app not available")
def test_http_index():
    """HTTP index should render wiki index as HTML."""
    client = TestClient(_http_app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Mob-Wiki" in resp.text or "Index" in resp.text


@pytest.mark.skipif(not _HTTP_AVAILABLE, reason="starlette/http_app not available")
def test_http_search_empty():
    """HTTP search without query should show search form."""
    client = TestClient(_http_app)
    resp = client.get("/search")
    assert resp.status_code == 200
    assert "Search" in resp.text
