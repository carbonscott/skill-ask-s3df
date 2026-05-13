#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# ///
"""Index documentation files into SQLite FTS5 for BM25 full-text search.

Usage:
    uv run docs_index.py index <docs_root> [--incremental] [--ext md rst py txt]
    uv run docs_index.py search <docs_root> <query> [--limit 10]
    uv run docs_index.py info <docs_root>
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

DB_NAME = "search.db"
DEFAULT_EXTENSIONS = {"md", "rst", "txt", "py"}


def create_schema(conn):
    """Create the documents metadata table and FTS5 virtual table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            path TEXT,
            filetype TEXT,
            modified REAL,
            size INTEGER,
            chunk_index INTEGER DEFAULT 0,
            heading TEXT,
            UNIQUE(path, chunk_index)
        )
    """)

    # FTS5 virtual tables do not support IF NOT EXISTS
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='documents_fts'"
    ).fetchone()
    if not existing:
        conn.execute("""
            CREATE VIRTUAL TABLE documents_fts USING fts5(
                title,
                body,
                tokenize='porter unicode61'
            )
        """)


def discover_files(docs_root, extensions):
    """Walk docs_root and yield (relative_path, absolute_path) for matching files.

    Skips hidden files/directories and the search database itself.
    """
    for dirpath, dirnames, filenames in os.walk(docs_root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in sorted(filenames):
            if filename.startswith(".") or filename == DB_NAME:
                continue
            ext = Path(filename).suffix.lstrip(".")
            if ext.lower() in extensions:
                abs_path = Path(dirpath) / filename
                if not abs_path.is_file():
                    continue
                rel_path = abs_path.relative_to(docs_root)
                yield (str(rel_path), abs_path)


def read_file_text(filepath):
    """Read file content as text. Returns None if unreadable or empty."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (IOError, OSError) as e:
        print(f"  Warning: cannot read {filepath}: {e}", file=sys.stderr)
        return None

    if not content.strip():
        return None
    return content


def index_files(docs_root, db_path, extensions, incremental=False):
    """Index documentation files into the SQLite FTS5 database.

    Returns (total_files, indexed_count, skipped_count, removed_count).
    """
    docs_root = Path(docs_root).resolve()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    if not incremental:
        conn.execute("DROP TABLE IF EXISTS documents_fts")
        conn.execute("DROP TABLE IF EXISTS documents")

    create_schema(conn)

    existing = {}
    if incremental:
        for row in conn.execute("SELECT id, path, modified FROM documents"):
            existing[row[1]] = (row[0], row[2])

    disk_files = list(discover_files(docs_root, extensions))
    disk_paths = {rel_path for rel_path, _ in disk_files}

    indexed = 0
    skipped = 0
    removed = 0

    for rel_path, abs_path in disk_files:
        stat = abs_path.stat()
        mtime = stat.st_mtime
        fsize = stat.st_size

        if incremental and rel_path in existing:
            old_id, old_mtime = existing[rel_path]
            if mtime == old_mtime:
                skipped += 1
                continue
            conn.execute("DELETE FROM documents_fts WHERE rowid = ?", (old_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (old_id,))
            print(f"  Updated: {rel_path}")
        else:
            print(f"  Indexing: {rel_path}")

        content = read_file_text(abs_path)
        if content is None:
            skipped += 1
            continue

        ext = Path(rel_path).suffix.lstrip(".")
        title = Path(rel_path).stem

        cursor = conn.execute(
            """INSERT OR REPLACE INTO documents
               (path, filetype, modified, size, chunk_index, heading)
               VALUES (?, ?, ?, ?, 0, NULL)""",
            (rel_path, ext, mtime, fsize),
        )
        doc_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO documents_fts(rowid, title, body) VALUES (?, ?, ?)",
            (doc_id, title, content),
        )
        indexed += 1

    if incremental:
        for old_path, (old_id, _) in existing.items():
            if old_path not in disk_paths:
                conn.execute("DELETE FROM documents_fts WHERE rowid = ?", (old_id,))
                conn.execute("DELETE FROM documents WHERE id = ?", (old_id,))
                removed += 1
                print(f"  Removed: {old_path}")

    conn.commit()
    conn.close()

    return (len(disk_files), indexed, skipped, removed)


def search_docs(db_path, query, limit=10):
    """Search the FTS5 index using BM25 ranking.

    Returns list of (path, filetype, title_highlight, snippet, score).
    """
    if not Path(db_path).exists():
        print(f"Error: database not found: {db_path}", file=sys.stderr)
        print("Run 'index' first to build the search database.", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)

    try:
        results = conn.execute(
            """
            SELECT
                d.path,
                d.filetype,
                highlight(documents_fts, 0, '>>>', '<<<'),
                snippet(documents_fts, 1, '>>>', '<<<', '...', 32),
                bm25(documents_fts)
            FROM documents_fts
            JOIN documents d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH ?
            ORDER BY bm25(documents_fts)
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError as e:
        error_msg = str(e)
        if "fts5: syntax error" in error_msg or "no such column" in error_msg:
            print(f"Error: invalid search query: {query}", file=sys.stderr)
            print(
                "Tip: use quotes for phrases, e.g. '\"mixed precision\"'",
                file=sys.stderr,
            )
            sys.exit(1)
        raise
    finally:
        conn.close()

    return results


def print_search_results(results, query):
    """Format and print search results to stdout."""
    if not results:
        print(f"No results found for: {query}")
        return

    print(f"Found {len(results)} result(s) for: {query}\n")

    for i, (path, filetype, title_hl, snippet, score) in enumerate(results, 1):
        print(f"{i}. {path} [{filetype}]")
        print(f"   Title: {title_hl}")
        snippet_clean = " ".join(snippet.split())
        print(f"   {snippet_clean}")
        print(f"   Score: {score:.6f}")
        print()


def show_info(db_path):
    """Display statistics about the search database."""
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Error: database not found: {db_path}", file=sys.stderr)
        print("Run 'index' first to build the search database.", file=sys.stderr)
        sys.exit(1)

    db_size = db_path.stat().st_size
    conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)

    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    total_size = conn.execute(
        "SELECT COALESCE(SUM(size), 0) FROM documents"
    ).fetchone()[0]

    type_counts = conn.execute(
        "SELECT filetype, COUNT(*), SUM(size) FROM documents "
        "GROUP BY filetype ORDER BY COUNT(*) DESC"
    ).fetchall()

    newest = conn.execute("SELECT MAX(modified) FROM documents").fetchone()[0]

    conn.close()

    print(f"Database: {db_path}")
    print(f"Database size: {db_size / 1024:.1f} KB")
    print(f"Indexed documents: {total}")
    print(f"Total content size: {total_size / 1024:.1f} KB")

    if newest:
        print(
            f"Last indexed file: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(newest))}"
        )

    if type_counts:
        print("\nBy file type:")
        for filetype, count, size in type_counts:
            print(f"  .{filetype}: {count} files ({size / 1024:.1f} KB)")


def build_parser():
    """Build the argument parser with index, search, and info subcommands."""
    parser = argparse.ArgumentParser(
        prog="docs_index",
        description="Index documentation files for full-text search using SQLite FTS5.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- index ---
    p_index = subparsers.add_parser(
        "index", help="Index documentation files into the search database."
    )
    p_index.add_argument("docs_root", help="Path to the documentation root directory.")
    p_index.add_argument(
        "--incremental",
        action="store_true",
        help="Only re-index files with changed modification time.",
    )
    p_index.add_argument(
        "--ext",
        nargs="+",
        default=None,
        metavar="EXT",
        help="File extensions to index without dots (default: md rst txt py).",
    )

    # --- search ---
    p_search = subparsers.add_parser("search", help="Search indexed documentation.")
    p_search.add_argument(
        "docs_root",
        help="Path to the documentation root directory (contains search.db).",
    )
    p_search.add_argument(
        "query", help="Search query (supports FTS5 syntax: phrases, OR, prefix*)."
    )
    p_search.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10).",
    )

    # --- info ---
    p_info = subparsers.add_parser("info", help="Show database statistics.")
    p_info.add_argument(
        "docs_root",
        help="Path to the documentation root directory (contains search.db).",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    docs_root = Path(args.docs_root).resolve()
    db_path = docs_root / DB_NAME

    if args.command == "index":
        if not docs_root.is_dir():
            print(f"Error: not a directory: {docs_root}", file=sys.stderr)
            sys.exit(1)

        extensions = set(args.ext) if args.ext else DEFAULT_EXTENSIONS

        mode = "incremental" if args.incremental else "full"
        print(f"Indexing {docs_root} ({mode} mode)")
        print(f"Extensions: {', '.join(sorted(extensions))}")
        print(f"Database: {db_path}\n")

        total, indexed, skipped, removed = index_files(
            docs_root, db_path, extensions, args.incremental
        )

        print(f"\nDone. {total} files found, {indexed} indexed, {skipped} skipped")
        if removed:
            print(f"{removed} removed (no longer on disk)")

    elif args.command == "search":
        results = search_docs(db_path, args.query, args.limit)
        print_search_results(results, args.query)

    elif args.command == "info":
        show_info(db_path)


if __name__ == "__main__":
    main()
