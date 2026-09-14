"""Mob-Wiki MCP server — 8 tools, HTTP viewer, and WikiServer core logic."""

import os
import sys
import hashlib
import tempfile
from html import escape
from pathlib import Path

from fastmcp import FastMCP
from indexer import WikiIndexer
from wiki_links import WikiLinks, wiki_targets

# ---------------------------------------------------------------------------
# WikiServer — core logic shared by MCP tools and tests
# ---------------------------------------------------------------------------


class WikiServer:
    """Pure-logic layer for all wiki operations."""

    def __init__(self, wiki_root: str | Path, db_path: str | Path):
        self.wiki_root = Path(wiki_root).resolve()
        self.db_path = Path(db_path)
        self.indexer = WikiIndexer(db_path=self.db_path, wiki_root=self.wiki_root)

    def _path(self, path: str, roots=("wiki", "raw")) -> Path:
        """Invariant: tools only access Markdown inside the permitted real subtree."""
        relative = Path(path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or relative.parts[0] not in roots
            or relative.suffix != ".md"
        ):
            raise ValueError(
                "Path must be a Markdown file inside " + "/ or ".join(roots) + "/"
            )
        full = self.wiki_root / relative
        # Reject symlinks, including parent directories and root aliases.
        if any(
            p.is_symlink()
            for p in [full, *full.parents]
            if p != self.wiki_root and p.is_relative_to(self.wiki_root)
        ):
            raise ValueError("Symlink paths are not allowed")
        if not full.resolve().is_relative_to(self.wiki_root / relative.parts[0]):
            raise ValueError("Path escapes allowed directory")
        return full

    # -- Query tools --------------------------------------------------------

    def wiki_list(self) -> dict:
        """Return the contents of wiki/index.md."""
        result = self.wiki_read("wiki/index.md")
        return {"index": result.get("content", "(index.md not found or inaccessible)")}

    def wiki_read(self, path: str) -> dict:
        """Read a .md file from wiki/ or raw/, parse frontmatter."""
        try:
            full_path = self._path(path)
        except ValueError as exc:
            return {"error": str(exc)}
        if not full_path.exists() or not full_path.is_file():
            return {"error": f"File not found: {path}"}
        content = full_path.read_text(encoding="utf-8")
        frontmatter, body = WikiIndexer.parse_frontmatter(content)
        return {
            "content": content,
            "frontmatter": frontmatter,
            "revision": hashlib.sha256(content.encode()).hexdigest(),
        }

    def wiki_search(self, query: str, limit: int = 10) -> dict:
        """Search the index for pages matching query."""
        results = self.indexer.search(query, limit=limit)
        return {"results": results}

    # -- Ingest tools -------------------------------------------------------

    def wiki_ingest(self, source_path: str) -> dict:
        """Read a raw/ source and return context for the LLM to decide actions."""
        try:
            full_path = self._path(source_path, ("raw",))
        except ValueError as exc:
            return {"error": str(exc)}
        if not full_path.exists() or not full_path.is_file():
            return {"error": f"Source not found: {source_path}"}

        source_content = full_path.read_text(encoding="utf-8")

        current_index = self.wiki_list()["index"]

        return {
            "source_path": source_path,
            "source_content": source_content,
            "current_index": current_index,
            "instructions": (
                "Read the source content above. Decide which wiki pages to "
                "create or update. Use wiki_create_page or wiki_update_page "
                "for each page, then update wiki/index.md and wiki/log.md."
            ),
        }

    def wiki_create_page(self, path: str, content: str) -> dict:
        """Create a new wiki page. Path must start with 'wiki/'."""
        try:
            full_path = self._path(path, ("wiki",))
        except ValueError as exc:
            return {"error": str(exc)}
        if full_path.exists():
            return {"error": f"Page already exists: {path}"}

        # Validate frontmatter has title
        frontmatter, _body = WikiIndexer.parse_frontmatter(content)
        if (
            not isinstance(frontmatter.get("title"), str)
            or not frontmatter["title"].strip()
        ):
            return {"error": "Frontmatter must include 'title'"}

        # Create parent directories and write file
        full_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with full_path.open("x", encoding="utf-8") as stream:
                stream.write(content)
        except FileExistsError:
            return {"error": f"Page already exists: {path}"}

        # Index the new page
        indexed = False
        try:
            self.indexer.index_page(path, content)
            indexed = True
        except Exception:
            pass

        return {"created": path, "indexed": indexed}

    def wiki_update_page(
        self, path: str, content: str, expected_revision: str | None = None
    ) -> dict:
        """Update an existing wiki page."""
        try:
            full_path = self._path(path, ("wiki",))
        except ValueError as exc:
            return {"error": str(exc)}
        if not full_path.is_file():
            return {"error": f"Page not found: {path}"}

        # Validate frontmatter has title
        frontmatter, _body = WikiIndexer.parse_frontmatter(content)
        if (
            not isinstance(frontmatter.get("title"), str)
            or not frontmatter["title"].strip()
        ):
            return {"error": "Frontmatter must include 'title'"}

        # Cross-process lock and revision check prevent cooperating clients from losing edits.
        from filelock import FileLock

        lock_dir = self.wiki_root / "db" / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        with FileLock(str(lock_dir / hashlib.sha256(path.encode()).hexdigest())):
            current = hashlib.sha256(full_path.read_bytes()).hexdigest()
            if expected_revision is not None and current != expected_revision:
                return {
                    "error": "Revision conflict: read the page again before updating",
                    "revision": current,
                }
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=full_path.parent, delete=False
            ) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            try:
                os.replace(tmp_path, full_path)
            finally:
                tmp_path.unlink(missing_ok=True)

        # Re-index the page
        indexed = False
        try:
            self.indexer.index_page(path, content)
            indexed = True
        except Exception:
            pass

        return {"updated": path, "indexed": indexed}

    # -- Maintenance tools --------------------------------------------------

    def wiki_lint(self) -> dict:
        """Scan wiki/ for structural issues."""
        issues: list[dict] = []
        wiki_dir = self.wiki_root / "wiki"
        if not wiki_dir.exists():
            return {"issues": issues}

        # Load index.md content for orphan detection
        index_content = self.wiki_list()["index"]
        indexed_pages = set(wiki_targets(index_content))

        # Collect all wiki pages (excluding index.md and log.md)
        all_pages: dict[str, str] = {}  # rel_path -> content
        for md_file in wiki_dir.rglob("*.md"):
            rel = str(md_file.relative_to(self.wiki_root))
            if md_file.is_symlink() or any(p.is_symlink() for p in md_file.parents):
                continue
            if md_file.name in ("index.md", "log.md"):
                continue
            if md_file.name == ".gitkeep":
                continue
            all_pages[rel] = md_file.read_text(encoding="utf-8")

        for rel_path, content in all_pages.items():
            meta, body = WikiIndexer.parse_frontmatter(content)

            # Missing frontmatter fields
            for field in ("title", "tags", "sources", "created", "updated"):
                if field not in meta:
                    issues.append(
                        {
                            "type": "missing_frontmatter",
                            "path": rel_path,
                            "description": f"Missing frontmatter field: {field}",
                        }
                    )

            # Broken wikilinks
            wikilinks = wiki_targets(body)
            for link in wikilinks:
                if not link:
                    continue
                try:
                    target = self._path(f"wiki/{link}.md", ("wiki",))
                    exists = target.is_file()
                except ValueError:
                    exists = False
                if not exists:
                    issues.append(
                        {
                            "type": "broken_wikilink",
                            "path": rel_path,
                            "description": f"Broken wikilink: [[{link}]]",
                        }
                    )

            # Orphan pages (not mentioned in index.md)
            # Extract the page slug from the path for matching
            # e.g. "wiki/concepts/san-system.md" -> check for "san-system" in index
            # Also check for the relative wikilink form: concepts/san-system
            wiki_rel = rel_path.removeprefix("wiki/").removesuffix(".md")
            if wiki_rel not in indexed_pages:
                issues.append(
                    {
                        "type": "orphan_page",
                        "path": rel_path,
                        "description": "Page not referenced in index.md",
                    }
                )

            # Stale pages (source file is newer than wiki page)
            sources = meta.get("sources", [])
            if isinstance(sources, list):
                wiki_mtime = self._committed_time(rel_path)
                for src in sources:
                    if not isinstance(src, str):
                        continue
                    try:
                        src_path = self._path(src, ("raw",))
                    except ValueError:
                        continue
                    if src_path.exists():
                        src_time = self._committed_time(src)
                        if (
                            src_time is not None
                            and wiki_mtime is not None
                            and src_time > wiki_mtime
                        ):
                            issues.append(
                                {
                                    "type": "stale_page",
                                    "path": rel_path,
                                    "description": f"Source {src} is newer than page",
                                }
                            )

        for link in indexed_pages:
            try:
                exists = self._path(f"wiki/{link}.md", ("wiki",)).is_file()
            except ValueError:
                exists = False
            if link and not exists:
                issues.append(
                    {
                        "type": "broken_wikilink",
                        "path": "wiki/index.md",
                        "description": f"Broken wikilink: [[{link}]]",
                    }
                )
        return {
            "issues": [i for i in issues if i["type"] != "stale_page"],
            "warnings": [i for i in issues if i["type"] == "stale_page"],
        }

    def _committed_time(self, path):
        """Checkout mtimes are not evidence that source content is newer."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct", "--", path],
                cwd=self.wiki_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return int(result.stdout.strip()) if result.stdout.strip() else None
        except (OSError, ValueError, subprocess.CalledProcessError):
            return None

    def wiki_rebuild_index(self) -> dict:
        """Rebuild the full search index."""
        return self.indexer.build_index()

    def close(self) -> None:
        """Close underlying indexer."""
        self.indexer.close()


# ---------------------------------------------------------------------------
# FastMCP server — 8 tools wrapping WikiServer
# ---------------------------------------------------------------------------

_wiki_server: WikiServer | None = None


def _get_server() -> WikiServer:
    """Lazy-init the global WikiServer instance."""
    global _wiki_server
    if _wiki_server is None:
        wiki_root = os.environ.get("WIKI_ROOT", str(Path(__file__).resolve().parent))
        db_dir = Path(wiki_root) / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "wiki.db"
        _wiki_server = WikiServer(wiki_root=wiki_root, db_path=db_path)
    return _wiki_server


mcp = FastMCP(
    "Mob-Wiki",
    instructions=(
        "Team knowledge base server. Use wiki_list/wiki_read/wiki_search to "
        "query knowledge. Use wiki_ingest to process raw sources. Use "
        "wiki_create_page/wiki_update_page to manage pages. Use wiki_lint "
        "and wiki_rebuild_index for maintenance."
    ),
)


@mcp.tool()
def wiki_list() -> dict:
    """List the wiki table of contents (index.md)."""
    return _get_server().wiki_list()


@mcp.tool()
def wiki_read(path: str) -> dict:
    """Read a wiki page or raw source. Returns content and parsed frontmatter."""
    return _get_server().wiki_read(path)


@mcp.tool()
def wiki_search(query: str, limit: int = 10) -> dict:
    """Search with local full-text search and Chinese substring fallback (no embeddings)."""
    return _get_server().wiki_search(query, limit=limit)


@mcp.tool()
def wiki_ingest(source_path: str) -> dict:
    """Read a raw/ source document and return it with the current index for LLM processing."""
    return _get_server().wiki_ingest(source_path)


@mcp.tool()
def wiki_create_page(path: str, content: str) -> dict:
    """Create a new wiki page. Path must start with 'wiki/'. Frontmatter must include title."""
    return _get_server().wiki_create_page(path, content)


@mcp.tool()
def wiki_update_page(
    path: str, content: str, expected_revision: str | None = None
) -> dict:
    """Update an existing wiki page. Frontmatter must include title."""
    return _get_server().wiki_update_page(path, content, expected_revision)


@mcp.tool()
def wiki_lint() -> dict:
    """Scan wiki/ for issues: broken links, orphan pages, stale pages, missing frontmatter."""
    return _get_server().wiki_lint()


@mcp.tool()
def wiki_rebuild_index() -> dict:
    """Rebuild the full search index from all wiki/ and raw/ files."""
    return _get_server().wiki_rebuild_index()


# ---------------------------------------------------------------------------
# HTTP viewer — optional, graceful if starlette/uvicorn missing
# ---------------------------------------------------------------------------

try:
    import markdown as md_lib
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import HTMLResponse
    from starlette.routing import Route

    _HAS_HTTP = True
except ImportError:
    _HAS_HTTP = False


def _render_html(title: str, body_html: str, nav: bool = True) -> str:
    """Wrap body HTML in a minimal page template."""
    title = escape(str(title))
    nav_html = ""
    if nav:
        nav_html = '<nav><a href="/">Index</a> | <a href="/search">Search</a></nav><hr>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Mob-Wiki</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 48rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
  nav {{ margin-bottom: 1rem; }}
  nav a {{ margin-right: 1rem; }}
  pre {{ background: #f4f4f4; padding: 1rem; overflow-x: auto; border-radius: 4px; }}
  code {{ background: #f4f4f4; padding: 0.15em 0.3em; border-radius: 3px; }}
  pre code {{ background: none; padding: 0; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
  th {{ background: #f4f4f4; }}
  a {{ color: #0366d6; }}
  .search-form {{ margin: 1rem 0; }}
  .search-form input[type=text] {{ padding: 0.4rem; width: 20rem; }}
  .result {{ margin: 1rem 0; padding: 0.5rem 0; border-bottom: 1px solid #eee; }}
  .result-path {{ color: #666; font-size: 0.85em; }}
</style>
</head>
<body>
{nav_html}
{body_html}
</body>
</html>"""


def _md_to_html(content: str) -> str:
    """Convert markdown content to HTML, handling frontmatter and wikilinks."""
    _meta, body = WikiIndexer.parse_frontmatter(content)
    import bleach

    html = md_lib.markdown(
        body, extensions=["fenced_code", "tables", "toc", WikiLinks()]
    )
    return bleach.clean(
        html,
        tags={
            "p",
            "a",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "li",
            "pre",
            "code",
            "blockquote",
            "strong",
            "em",
            "hr",
            "br",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "img",
            "del",
        },
        attributes={
            "a": ["href", "title"],
            "img": ["src", "alt", "title"],
            "*": ["id", "class"],
        },
        strip=True,
    )


if _HAS_HTTP:

    async def _index_page(request: Request) -> HTMLResponse:
        """GET / -> render wiki/index.md."""
        srv = _get_server()
        result = srv.wiki_list()
        html = _md_to_html(result["index"])
        return HTMLResponse(_render_html("Index", html))

    async def _wiki_page(request: Request) -> HTMLResponse:
        """GET /wiki/{path:path} -> render a wiki page."""
        path = "wiki/" + request.path_params["path"]
        srv = _get_server()
        result = srv.wiki_read(path)
        if "error" in result:
            return HTMLResponse(
                _render_html("Not Found", f"<p>{escape(result['error'])}</p>"),
                status_code=404,
            )
        html = _md_to_html(result["content"])
        title = result["frontmatter"].get("title", path)
        return HTMLResponse(_render_html(title, html))

    async def _raw_page(request: Request) -> HTMLResponse:
        """GET /raw/{path:path} -> render a raw source."""
        path = "raw/" + request.path_params["path"]
        srv = _get_server()
        result = srv.wiki_read(path)
        if "error" in result:
            return HTMLResponse(
                _render_html("Not Found", f"<p>{escape(result['error'])}</p>"),
                status_code=404,
            )
        html = _md_to_html(result["content"])
        title = result["frontmatter"].get("title", path)
        return HTMLResponse(_render_html(title, html))

    async def _search_page(request: Request) -> HTMLResponse:
        """GET /search?q= -> search form + results."""
        query = request.query_params.get("q", "")
        body_parts = [
            "<h1>Search</h1>",
            '<form class="search-form" method="get" action="/search">',
            f'<input type="text" name="q" value="{escape(query, quote=True)}" placeholder="Search wiki...">',
            ' <button type="submit">Search</button>',
            "</form>",
        ]

        if query:
            srv = _get_server()
            result = srv.wiki_search(query)
            results = result.get("results", [])
            if results:
                for r in results:
                    path = escape(r["path"], quote=True)
                    title = escape(str(r.get("title", path)))
                    snippet = escape(r.get("snippet", "")[:150])
                    href = f"/{path}"
                    body_parts.append(
                        f'<div class="result">'
                        f'<a href="{href}"><strong>{title}</strong></a>'
                        f'<div class="result-path">{path}</div>'
                        f"<div>{snippet}</div>"
                        f"</div>"
                    )
            else:
                body_parts.append("<p>No results found.</p>")

        body_html = "\n".join(body_parts)
        return HTMLResponse(_render_html("Search", body_html))

    _http_app = Starlette(
        routes=[
            Route("/", _index_page),
            Route("/wiki/{path:path}", _wiki_page),
            Route("/raw/{path:path}", _raw_page),
            Route("/search", _search_page),
        ],
    )
else:
    _http_app = None


# ---------------------------------------------------------------------------
# main() — start HTTP in background, run MCP on stdio
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: build index, start HTTP viewer, run MCP server."""
    import threading
    import argparse

    parser = argparse.ArgumentParser(
        description="Mob-Wiki MCP server or local read-only viewer"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run the standalone local HTTP viewer instead of MCP",
    )
    args = parser.parse_args()

    # Ensure server is initialised and index is built
    srv = _get_server()
    stats = srv.wiki_rebuild_index()
    print(f"Index built: {stats['pages_indexed']} pages", file=sys.stderr)

    if args.http:
        import uvicorn

        uvicorn.run(
            _http_app,
            host="127.0.0.1",
            port=int(os.environ.get("WIKI_HTTP_PORT", "8787")),
        )
        return

    # Start HTTP viewer in background thread (optional)
    if (
        _HAS_HTTP
        and _http_app is not None
        and os.environ.get("WIKI_HTTP_ENABLED", "0") == "1"
    ):
        try:
            import uvicorn

            http_port = int(os.environ.get("WIKI_HTTP_PORT", "8787"))

            def _run_http() -> None:
                uvicorn.run(
                    _http_app,
                    host="127.0.0.1",
                    port=http_port,
                    log_level="warning",
                )

            http_thread = threading.Thread(target=_run_http, daemon=True)
            http_thread.start()
            print(f"HTTP viewer: http://127.0.0.1:{http_port}", file=sys.stderr)
        except ImportError:
            print("uvicorn not installed — HTTP viewer disabled", file=sys.stderr)

    # Run MCP server (blocking, stdio transport)
    mcp.run()


if __name__ == "__main__":
    main()
