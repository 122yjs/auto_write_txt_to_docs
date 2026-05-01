import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple


class CacheDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_tables(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS line_cache (
                    hash TEXT PRIMARY KEY,
                    line_preview TEXT,
                    first_seen_at REAL,
                    last_seen_at REAL,
                    occurrence_count INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_state (
                    filepath TEXT PRIMARY KEY,
                    last_byte_offset INTEGER,
                    file_ctime_ns INTEGER,
                    file_mtime_ns INTEGER,
                    last_attempt_time REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS provenance (
                    hash TEXT,
                    source_file TEXT,
                    first_seen_at REAL,
                    PRIMARY KEY (hash, source_file)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_line_cache_last_seen ON line_cache(last_seen_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_provenance_hash ON provenance(hash)
            """)

    def is_duplicate(self, line_hash: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("SELECT 1 FROM line_cache WHERE hash = ?", (line_hash,))
            return cursor.fetchone() is not None

    def add_line(self, line_hash: str, line_preview: str):
        now = sqlite3.time.time() if hasattr(sqlite3, 'time') else __import__('time').time()
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO line_cache (hash, line_preview, first_seen_at, last_seen_at, occurrence_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(hash) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    occurrence_count = occurrence_count + 1
            """, (line_hash, line_preview, now, now))

    def get_duplicate_stats(self, limit: int = 10) -> List[Tuple]:
        with self._connect() as conn:
            cursor = conn.execute("""
                SELECT hash, line_preview, occurrence_count
                FROM line_cache
                ORDER BY occurrence_count DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()

    def migrate_from_json(self, cache_json_path: str, stats_json_path: Optional[str] = None):
        if os.path.exists(cache_json_path):
            with open(cache_json_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            if isinstance(cache_data, dict):
                for h, line in cache_data.items():
                    preview = line[:80] + "..." if len(line) > 80 else line
                    self.add_line(str(h), preview)
        if stats_json_path and os.path.exists(stats_json_path):
            with open(stats_json_path, 'r', encoding='utf-8') as f:
                stats_data = json.load(f)
            if isinstance(stats_data, dict):
                with self._connect() as conn:
                    for h, stat in stats_data.items():
                        conn.execute("""
                            INSERT INTO line_cache (hash, line_preview, first_seen_at, last_seen_at, occurrence_count)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(hash) DO UPDATE SET
                                occurrence_count = occurrence_count + excluded.occurrence_count
                        """, (
                            str(h),
                            stat.get("line_preview", ""),
                            stat.get("first_seen_at", 0),
                            stat.get("last_seen_at", 0),
                            stat.get("total_occurrences", 1),
                        ))

    def get_cache_size(self) -> int:
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM line_cache")
            return cursor.fetchone()[0]

    def close(self):
        pass
