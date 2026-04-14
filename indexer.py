"""Wiki search indexer — FTS5 keyword search + sqlite-vec embedding similarity."""

import os
import re
import sqlite3
import struct
from pathlib import Path

import yaml

# sqlite-vec is optional — embedding search degrades gracefully
try:
    import sqlite_vec

    _HAS_VEC = True
except ImportError:
    _HAS_VEC = False


EMBEDDING_DIM = 1536  # text-embedding-3-small


def _float_list_to_blob(floats: list[float]) -> bytes:
    """Pack a list of floats into a binary blob for sqlite-vec."""
    return struct.pack(f"{len(floats)}f", *floats)


class WikiIndexer:
    """Hybrid search index backed by SQLite FTS5 and sqlite-vec."""

    def __init__(
        self,
        db_path: str | Path,
        wiki_root: str | Path,
        embedding_enabled: bool = True,
    ):
        self.db_path = str(db_path)
        self.wiki_root = Path(wiki_root)
        self.embedding_enabled = embedding_enabled and _HAS_VEC

        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        # Load sqlite-vec extension if available
        self._vec_loaded = False
        if _HAS_VEC:
            try:
                self._conn.enable_load_extension(True)
                sqlite_vec.load(self._conn)
                self._conn.enable_load_extension(False)
                self._vec_loaded = True
            except Exception:
                self._vec_loaded = False

        self._openai_client = None
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema setup
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        cur = self._conn.cursor()

        # Core pages table
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

        # FTS5 virtual table — content-synced with pages
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                path, title, body,
                content=pages, content_rowid=rowid
            )
            """
        )

        # Triggers to keep FTS in sync with pages table
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

        # Embeddings table (only when sqlite-vec is available)
        if self._vec_loaded:
            cur.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS page_embeddings USING vec0(
                    path TEXT PRIMARY KEY,
                    embedding float[{EMBEDDING_DIM}]
                )
                """
            )

        self._conn.commit()

    # ------------------------------------------------------------------
    # Frontmatter parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict, str]:
        """Split YAML frontmatter from markdown body.

        Returns (metadata_dict, body_text).  If no frontmatter is found,
        returns an empty dict and the full content as body.
        """
        pattern = r"^---\s*\n(.*?)\n---\s*\n?(.*)"
        match = re.match(pattern, content, re.DOTALL)
        if not match:
            return {}, content

        yaml_str, body = match.group(1), match.group(2)
        try:
            meta = yaml.safe_load(yaml_str) or {}
        except yaml.YAMLError:
            meta = {}

        return meta, body

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_page(self, rel_path: str, content: str | None = None) -> None:
        """Add or update a single page in the index.

        If *content* is ``None``, reads the file from disk.
        """
        if content is None:
            full_path = self.wiki_root / rel_path
            if not full_path.exists():
                return
            content = full_path.read_text(encoding="utf-8")

        meta, body = self.parse_frontmatter(content)
        title = meta.get("title", rel_path)
        tags_raw = meta.get("tags", [])
        if isinstance(tags_raw, list):
            tags = ",".join(str(t) for t in tags_raw)
        else:
            tags = str(tags_raw)
        updated = str(meta.get("updated", ""))

        cur = self._conn.cursor()

        # Upsert: delete then insert (triggers keep FTS in sync)
        cur.execute("DELETE FROM pages WHERE path = ?", (rel_path,))
        cur.execute(
            "INSERT INTO pages (path, title, tags, body, updated) VALUES (?, ?, ?, ?, ?)",
            (rel_path, title, tags, body, updated),
        )
        self._conn.commit()

        # Embedding (non-fatal)
        if self.embedding_enabled and self._vec_loaded:
            combined = f"{title}\n{body}"
            try:
                self._index_embedding(rel_path, combined)
            except Exception:
                pass  # graceful degradation

    def remove_page(self, rel_path: str) -> None:
        """Remove a page from the index."""
        cur = self._conn.cursor()
        cur.execute("DELETE FROM pages WHERE path = ?", (rel_path,))

        if self._vec_loaded:
            try:
                cur.execute(
                    "DELETE FROM page_embeddings WHERE path = ?", (rel_path,)
                )
            except Exception:
                pass

        self._conn.commit()

    def build_index(self) -> dict:
        """Rebuild the entire index from wiki/ and raw/ directories.

        Returns a summary dict with pages_indexed and embeddings_generated.
        """
        cur = self._conn.cursor()

        # Wipe existing data
        cur.execute("DELETE FROM pages")
        if self._vec_loaded:
            try:
                cur.execute("DELETE FROM page_embeddings")
            except Exception:
                pass
        self._conn.commit()

        pages_indexed = 0
        embeddings_generated = 0

        # Walk wiki/ and raw/ for .md files
        for subdir in ("wiki", "raw"):
            base = self.wiki_root / subdir
            if not base.exists():
                continue
            for md_file in base.rglob("*.md"):
                rel_path = str(md_file.relative_to(self.wiki_root))
                content = md_file.read_text(encoding="utf-8")
                self.index_page(rel_path, content)
                pages_indexed += 1

                # Count embeddings (check if one was written)
                if self.embedding_enabled and self._vec_loaded:
                    row = cur.execute(
                        "SELECT 1 FROM page_embeddings WHERE path = ?",
                        (rel_path,),
                    ).fetchone()
                    if row:
                        embeddings_generated += 1

        return {
            "pages_indexed": pages_indexed,
            "embeddings_generated": embeddings_generated,
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Hybrid search: FTS5 + embedding, merged with RRF."""
        fts_results = self._search_fts(query, limit)

        if self.embedding_enabled and self._vec_loaded:
            try:
                emb_results = self._search_embedding(query, limit)
            except Exception:
                emb_results = []
        else:
            emb_results = []

        if emb_results:
            merged = self._rrf_merge(fts_results, emb_results)
        else:
            merged = fts_results

        return merged[:limit]

    def _search_fts(self, query: str, limit: int = 10) -> list[dict]:
        """Full-text search using FTS5 BM25."""
        sanitized = self._sanitize_fts_query(query)
        if not sanitized:
            return []

        cur = self._conn.cursor()
        try:
            rows = cur.execute(
                """
                SELECT p.path, p.title, p.body,
                       rank AS score
                FROM pages_fts
                JOIN pages p ON p.path = pages_fts.path
                WHERE pages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (sanitized, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        results = []
        for row in rows:
            body = row["body"] or ""
            snippet = body.strip()[:200]
            results.append(
                {
                    "path": row["path"],
                    "title": row["title"],
                    "score": float(row["score"]),
                    "snippet": snippet,
                }
            )
        return results

    def _search_embedding(self, query: str, limit: int = 10) -> list[dict]:
        """Semantic search using sqlite-vec cosine distance."""
        if not self._vec_loaded:
            return []

        query_emb = self._get_embedding(query)
        if not query_emb:
            return []

        blob = _float_list_to_blob(query_emb)
        cur = self._conn.cursor()
        rows = cur.execute(
            """
            SELECT pe.path, pe.distance,
                   p.title, p.body
            FROM page_embeddings pe
            JOIN pages p ON p.path = pe.path
            WHERE pe.embedding MATCH ?
            ORDER BY pe.distance
            LIMIT ?
            """,
            (blob, limit),
        ).fetchall()

        results = []
        for row in rows:
            body = row["body"] or ""
            snippet = body.strip()[:200]
            # Convert distance to a score (lower distance = better)
            results.append(
                {
                    "path": row["path"],
                    "title": row["title"],
                    "score": -float(row["distance"]),
                    "snippet": snippet,
                }
            )
        return results

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def _index_embedding(self, rel_path: str, text: str) -> None:
        """Compute and store an embedding for a page."""
        emb = self._get_embedding(text)
        if not emb:
            return

        blob = _float_list_to_blob(emb)
        cur = self._conn.cursor()
        # Upsert: delete then insert
        try:
            cur.execute(
                "DELETE FROM page_embeddings WHERE path = ?", (rel_path,)
            )
        except Exception:
            pass
        cur.execute(
            "INSERT INTO page_embeddings (path, embedding) VALUES (?, ?)",
            (rel_path, blob),
        )
        self._conn.commit()

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding from OpenAI API.  Returns empty list on failure."""
        try:
            if self._openai_client is None:
                from openai import OpenAI

                self._openai_client = OpenAI()

            resp = self._openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],  # stay within token limits
            )
            return resp.data[0].embedding
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Reciprocal Rank Fusion
    # ------------------------------------------------------------------

    @staticmethod
    def _rrf_merge(*result_lists: list[dict], k: int = 60) -> list[dict]:
        """Merge multiple ranked result lists using Reciprocal Rank Fusion.

        score(doc) = sum( 1 / (k + rank + 1) ) across all lists
        where rank is 0-based position in each list.
        """
        scores: dict[str, float] = {}
        docs: dict[str, dict] = {}

        for result_list in result_lists:
            for rank, doc in enumerate(result_list):
                path = doc["path"]
                scores[path] = scores.get(path, 0.0) + 1.0 / (k + rank + 1)
                if path not in docs:
                    docs[path] = doc

        # Build merged list sorted by RRF score descending
        merged = []
        for path in sorted(scores, key=lambda p: scores[p], reverse=True):
            entry = dict(docs[path])
            entry["score"] = scores[path]
            merged.append(entry)

        return merged

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        """Sanitize a user query for FTS5 MATCH.

        Strips special FTS5 syntax characters and joins terms with OR.
        """
        # Remove FTS5 special characters
        cleaned = re.sub(r'["\'\*\(\)\-\+\^:]', " ", query)
        terms = cleaned.split()
        if not terms:
            return ""
        # Join with OR so any term matching counts
        return " OR ".join(terms)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
