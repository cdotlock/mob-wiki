"""Wiki search indexer — SQLite FTS5 keyword search only."""

import re
import sqlite3
import threading
from functools import wraps
from pathlib import Path

import yaml


def locked(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapped


class WikiIndexer:
    """BM25 full-text search index backed by SQLite FTS5."""

    def __init__(self, db_path: str | Path, wiki_root: str | Path):
        self.db_path = str(db_path)
        self.wiki_root = Path(wiki_root)
        self._lock = threading.RLock()
        self._building = False
        self._snapshot = None
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                path    TEXT PRIMARY KEY,
                title   TEXT,
                tags    TEXT,
                body    TEXT,
                updated TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                path, title, body,
                content=pages, content_rowid=rowid
            )
            """
        )
        cur.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS pages_ai AFTER INSERT ON pages BEGIN
                INSERT INTO pages_fts(rowid, path, title, body)
                VALUES (new.rowid, new.path, new.title, new.body);
            END;
            CREATE TRIGGER IF NOT EXISTS pages_ad AFTER DELETE ON pages BEGIN
                INSERT INTO pages_fts(pages_fts, rowid, path, title, body)
                VALUES ('delete', old.rowid, old.path, old.title, old.body);
            END;
            CREATE TRIGGER IF NOT EXISTS pages_au AFTER UPDATE ON pages BEGIN
                INSERT INTO pages_fts(pages_fts, rowid, path, title, body)
                VALUES ('delete', old.rowid, old.path, old.title, old.body);
                INSERT INTO pages_fts(rowid, path, title, body)
                VALUES (new.rowid, new.path, new.title, new.body);
            END;
            """
        )
        self._conn.commit()

    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict, str]:
        """Split YAML frontmatter from markdown body."""
        pattern = r"^---\s*\n(.*?)\n---\s*\n?(.*)"
        match = re.match(pattern, content, re.DOTALL)
        if not match:
            return {}, content
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        return meta if isinstance(meta, dict) else {}, match.group(2)

    @locked
    def index_page(self, rel_path: str, content: str | None = None) -> None:
        """Add or update a single page in the index."""
        if content is None:
            full_path = self.wiki_root / rel_path
            if not full_path.exists():
                return
            content = full_path.read_text(encoding="utf-8")

        meta, body = self.parse_frontmatter(content)
        title = str(meta.get("title", rel_path))
        tags_raw = meta.get("tags", [])
        tags = (
            ",".join(str(t) for t in tags_raw)
            if isinstance(tags_raw, list)
            else str(tags_raw)
        )
        updated = str(meta.get("updated", ""))

        cur = self._conn.cursor()
        cur.execute("DELETE FROM pages WHERE path = ?", (rel_path,))
        cur.execute(
            "INSERT INTO pages (path, title, tags, body, updated) VALUES (?, ?, ?, ?, ?)",
            (rel_path, title, tags, body, updated),
        )
        if not self._building:
            self._conn.commit()

    @locked
    def remove_page(self, rel_path: str) -> None:
        """Remove a page from the index."""
        self._conn.execute("DELETE FROM pages WHERE path = ?", (rel_path,))
        self._conn.commit()

    def _files(self):
        return sorted(
            p
            for root in ("wiki", "raw")
            for p in (self.wiki_root / root).rglob("*.md")
            if not p.is_symlink()
            and not any(parent.is_symlink() for parent in p.parents)
        )

    def _state(self):
        return [(str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in self._files()]

    @locked
    def build_index(self) -> dict:
        """Rebuild the entire index from wiki/ and raw/ directories."""
        state = self._state()
        files = self._files()
        self._building = True
        try:
            with self._conn:
                self._conn.execute("DELETE FROM pages")
                for md_file in files:
                    self.index_page(
                        str(md_file.relative_to(self.wiki_root)),
                        md_file.read_text(encoding="utf-8"),
                    )
            self._snapshot = state
        finally:
            self._building = False
        return {"pages_indexed": len(files)}

    @locked
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """BM25 full-text search."""
        if self._snapshot != self._state():
            self.build_index()
        tokens = re.findall(r"\w+", query, re.UNICODE)
        if not tokens:
            return []
        limit = max(1, min(limit, 100))
        fts_query = " OR ".join('"' + token + '"' for token in tokens)

        try:
            rows = self._conn.execute(
                """
                SELECT p.path, p.title, p.body, rank AS score
                FROM pages_fts
                JOIN pages p ON p.path = pages_fts.path
                WHERE pages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        # FTS5's unicode tokenizer keeps Chinese sentences together. Substring
        # fallback makes ordinary Chinese words discoverable without an API key.
        if not rows and any(re.search(r"[\u3400-\u9fff]", token) for token in tokens):
            clauses = " OR ".join(
                "(instr(title, ?) > 0 OR instr(body, ?) > 0)" for _ in tokens
            )
            args = [value for token in tokens for value in (token, token)]
            rows = self._conn.execute(
                f"SELECT path, title, body, 0.0 AS score FROM pages WHERE {clauses} ORDER BY path LIMIT ?",
                [*args, limit],
            ).fetchall()
        return [
            {
                "path": row["path"],
                "title": row["title"],
                "score": float(row["score"]),
                "snippet": (row["body"] or "").strip()[:200],
            }
            for row in rows
        ]

    @locked
    def close(self) -> None:
        self._conn.close()
