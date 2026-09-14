"""Regression coverage for team restart failures and content isolation."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from server import WikiServer, _md_to_html, _render_html
from wiki_links import wiki_targets
from indexer import WikiIndexer


@pytest.fixture
def srv(tmp_path):
    (tmp_path / "wiki").mkdir()
    (tmp_path / "raw").mkdir()
    (tmp_path / "wiki/index.md").write_text("---\ntitle: Index\n---\n[[page]]")
    (tmp_path / "wiki/page.md").write_text("---\ntitle: Page\n---\n团队知识库管理")
    server = WikiServer(tmp_path, tmp_path / "index.db")
    yield server
    server.close()


@pytest.mark.parametrize(
    "path",
    [
        "../secret.md",
        "/tmp/secret.md",
        "wiki/../../secret.md",
        "schema.md",
        "wiki/../raw/source.md",
    ],
)
def test_path_escape_rejected(srv, path):
    assert "error" in srv.wiki_read(path)
    assert "error" in srv.wiki_create_page(path, "---\ntitle: Test\n---\n")
    assert "error" in srv.wiki_update_page(path, "---\ntitle: Test\n---\n")


def test_raw_is_immutable_and_symlinks_blocked(srv, tmp_path):
    source = tmp_path / "raw/source.md"
    source.write_text("original")
    assert "error" in srv.wiki_update_page("raw/source.md", "---\ntitle: Test\n---\n")
    (tmp_path / "wiki/link.md").symlink_to(source)
    assert "error" in srv.wiki_read("wiki/link.md")
    assert "error" in srv.wiki_update_page("wiki/link.md", "---\ntitle: Test\n---\n")
    assert source.read_text() == "original"
    assert srv.wiki_rebuild_index()["pages_indexed"] == 3


def test_revision_conflict_keeps_newer_content(srv):
    revision = srv.wiki_read("wiki/page.md")["revision"]
    content = "---\ntitle: New\n---\nnew content"
    assert "error" not in srv.wiki_update_page("wiki/page.md", content, revision)
    assert "error" in srv.wiki_update_page(
        "wiki/page.md", "---\ntitle: Old\n---\n", revision
    )
    assert srv.wiki_read("wiki/page.md")["content"] == content


def test_search_fresh_chinese_and_threads(srv, tmp_path):
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: srv.wiki_search("知识库"), range(4)))
    assert all(r["results"][0]["path"] == "wiki/page.md" for r in results)
    (tmp_path / "wiki/page.md").write_text(
        "---\ntitle: Replacement\n---\nnewuniquetoken"
    )
    assert srv.wiki_search("newuniquetoken")["results"]
    (tmp_path / "wiki/page.md").unlink()
    assert not srv.wiki_search("newuniquetoken")["results"]


def test_markdown_links_ignore_code_and_support_aliases():
    content = '[[concepts/page#heading|Label]]\n\n`[[inline]]`\n\n```sh\n[[ -n "$X" ]]\n```\n\n    [[indented]]\n'
    assert wiki_targets(content) == ["concepts/page"]
    rendered = _md_to_html(content)
    assert 'href="/wiki/concepts/page.md#heading"' in rendered
    assert ">Label</a>" in rendered
    assert 'href="/wiki/inline' not in rendered


def test_viewer_sanitizes_html_and_titles():
    content = '<script>alert(1)</script><img src="x" onerror="alert(2)">\n\n[bad](javascript:alert)'
    rendered = _md_to_html(content)
    assert "<script>" not in rendered
    assert "onerror=" not in rendered
    assert 'href="javascript:' not in rendered
    assert "<title>&lt;script&gt;" in _render_html("<script>", "")


@pytest.mark.parametrize("yaml", ["- one\n- two", "42", "true", '"string"'])
def test_non_mapping_frontmatter(yaml):
    assert WikiIndexer.parse_frontmatter("---\n" + yaml + "\n---\nBody") == ({}, "Body")


def test_fts_punctuation_is_literal(srv, tmp_path):
    (tmp_path / "wiki/page.md").write_text("---\ntitle: OR\n---\nagent v2.1 foo/bar")
    for query in ["OR", "v2.1", "foo/bar", "agent?"]:
        assert srv.wiki_search(query)["results"]


def test_rebuild_failure_preserves_previous_index(srv, tmp_path):
    srv.wiki_rebuild_index()
    (tmp_path / "wiki/bad.md").write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        srv.wiki_rebuild_index()
    assert srv.indexer._conn.execute("SELECT count(*) FROM pages").fetchone()[0] == 2


def test_http_search_escapes_input(srv, monkeypatch):
    import server
    from starlette.testclient import TestClient

    monkeypatch.setattr(server, "_wiki_server", srv)
    with TestClient(server._http_app) as client:
        response = client.get("/search", params={"q": '"><script>alert(1)</script>'})
        assert response.status_code == 200
        assert "<script>" not in response.text


def test_default_root_is_not_callers_directory(monkeypatch, tmp_path):
    import server

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WIKI_ROOT", raising=False)
    monkeypatch.setattr(server, "_wiki_server", None)
    instance = server._get_server()
    try:
        assert (
            instance.wiki_root
            == __import__("pathlib").Path(server.__file__).resolve().parent
        )
    finally:
        instance.close()


def test_lint_checks_index_targets_and_not_substring_mentions(srv, tmp_path):
    (tmp_path / "wiki/index.md").write_text("---\ntitle: Index\n---\n[[page-longer]]")
    issues = srv.wiki_lint()["issues"]
    assert any(
        i["type"] == "broken_wikilink" and i["path"] == "wiki/index.md" for i in issues
    )
    assert any(
        i["type"] == "orphan_page" and i["path"] == "wiki/page.md" for i in issues
    )


def test_source_age_uses_git_evidence_not_checkout_time(srv, tmp_path, monkeypatch):
    page = tmp_path / "wiki/page.md"
    page.write_text(
        "---\ntitle: Page\ntags: [test]\nsources: [raw/source.md]\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\nPage"
    )
    (tmp_path / "raw/source.md").write_text("new source")
    monkeypatch.setattr(
        srv, "_committed_time", lambda path: 20 if path.startswith("raw/") else 10
    )
    result = srv.wiki_lint()
    assert result["issues"] == []
    assert result["warnings"][0]["type"] == "stale_page"
    monkeypatch.setattr(srv, "_committed_time", lambda path: None)
    assert srv.wiki_lint()["warnings"] == []
