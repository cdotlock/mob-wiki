"""Wiki search indexer — SQLite FTS5 keyword search only."""

import os
import re
import sqlite3
from pathlib import Path

import yaml


class WikiIndexer:
    """BM25 full-text search index backed by SQLite FTS5."""

    def __init__(self, db_path: str | Path, wiki_root: str | Path):
        self.db_path = str(db_path)
        self.wiki_root = Path(wiki_root)
        self._conn = sqlite3.connect(self.db_path)
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
        return meta, match.group(2)

    def index_page(self, rel_path: str, content: str | None = None) -> None:
        """Add or update a single page in the index."""
        if content is None:
            full_path = self.wiki_root / rel_path
            if not full_path.exists():
                return
            content = full_path.read_text(encoding="utf-8")

        meta, body = self.parse_frontmatter(content)
        title = meta.get("title", rel_path)
        tags_raw = meta.get("tags", [])
        tags = ",".join(str(t) for t in tags_raw) if isinstance(tags_raw, list) else str(tags_raw)
        updated = str(meta.get("updated", ""))

        cur = self._conn.cursor()
        cur.execute("DELETE FROM pages WHERE path = ?", (rel_path,))
        cur.execute(
            "INSERT INTO pages (path, title, tags, body, updated) VALUES (?, ?, ?, ?, ?)",
            (rel_path, title, tags, body, updated),
        )
        self._conn.commit()

    def remove_page(self, rel_path: str) -> None:
        """Remove a page from the index."""
        self._conn.execute("DELETE FROM pages WHERE path = ?", (rel_path,))
        self._conn.commit()

    def build_index(self) -> dict:
        """Rebuild the entire index from wiki/ and raw/ directories."""
        self._conn.execute("DELETE FROM pages")
        self._conn.commit()

        count = 0
        for subdir in ("wiki", "raw"):
            base = self.wiki_root / subdir
            if not base.exists():
                continue
            for md_file in base.rglob("*.md"):
                rel_path = str(md_file.relative_to(self.wiki_root))
                content = md_file.read_text(encoding="utf-8")
                self.index_page(rel_path, content)
                count += 1

        return {"pages_indexed": count}

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """BM25 full-text search."""
        sanitized = re.sub(r'["\'\*\(\)\-\+\^:]', " ", query).strip()
        if not sanitized:
            return []
        fts_query = " OR ".join(sanitized.split())

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

        return [
            {
                "path": row["path"],
                "title": row["title"],
                "score": float(row["score"]),
                "snippet": (row["body"] or "").strip()[:200],
            }
            for row in rows
        ]

    def close(self) -> None:
        self._conn.close()
