import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("REFINERY_DB_PATH", "/persist/refinery/refinery.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY,
    media_type    TEXT NOT NULL,            -- 'music', 'video', 'book', 'game'
    status        TEXT NOT NULL DEFAULT 'processing',
                                            -- processing, ready, approved, rejected, failed
    source_path   TEXT NOT NULL UNIQUE,
    title         TEXT,                     -- album/movie/book/game title
    artist        TEXT,                     -- artist / director / author / dev
    year          INTEGER,
    genre         TEXT,
    cover_url     TEXT,
    cover_local   TEXT,
    meta_json     TEXT,                     -- everything else
    error         TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at  TIMESTAMP,
    decided_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracks (
    id            INTEGER PRIMARY KEY,
    item_id       INTEGER NOT NULL,
    source_path   TEXT NOT NULL,
    track_no      INTEGER,
    disc_no       INTEGER DEFAULT 1,
    title         TEXT,
    duration_secs INTEGER,
    lyrics_synced TEXT,
    lyrics_plain  TEXT,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_tracks_item  ON tracks(item_id);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)
        # Lightweight migrations for columns added after first deploy.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tracks)").fetchall()}
        if "lyrics_synced" not in cols:
            conn.execute("ALTER TABLE tracks ADD COLUMN lyrics_synced TEXT")
        if "lyrics_plain" not in cols:
            conn.execute("ALTER TABLE tracks ADD COLUMN lyrics_plain TEXT")
