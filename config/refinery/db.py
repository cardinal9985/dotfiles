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
    spectrogram_local TEXT,
    meta_json     TEXT,                     -- everything else
    error         TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at  TIMESTAMP,
    decided_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracks (
    id             INTEGER PRIMARY KEY,
    item_id        INTEGER NOT NULL,
    source_path    TEXT NOT NULL,
    track_no       INTEGER,
    disc_no        INTEGER DEFAULT 1,
    title          TEXT,
    duration_secs  INTEGER,
    lyrics_synced  TEXT,
    lyrics_plain   TEXT,
    quality_ok     INTEGER,   -- 1 = decoder verified clean, 0 = failed
    quality_cutoff INTEGER,   -- spectral cutoff Hz
    quality_verdict TEXT,     -- 'verified', 'borderline', 'suspect', 'unknown'
    quality_error  TEXT,
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
        if "quality_ok" not in cols:
            conn.execute("ALTER TABLE tracks ADD COLUMN quality_ok INTEGER")
        if "quality_cutoff" not in cols:
            conn.execute("ALTER TABLE tracks ADD COLUMN quality_cutoff INTEGER")
        if "quality_verdict" not in cols:
            conn.execute("ALTER TABLE tracks ADD COLUMN quality_verdict TEXT")
        if "quality_error" not in cols:
            conn.execute("ALTER TABLE tracks ADD COLUMN quality_error TEXT")
        item_cols = {r["name"] for r in conn.execute("PRAGMA table_info(items)").fetchall()}
        if "spectrogram_local" not in item_cols:
            conn.execute("ALTER TABLE items ADD COLUMN spectrogram_local TEXT")
        if "artist_photo_local" not in item_cols:
            conn.execute("ALTER TABLE items ADD COLUMN artist_photo_local TEXT")
