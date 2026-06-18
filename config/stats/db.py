import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.environ.get("STATS_DB_PATH", "/data/stats.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    source TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_name TEXT,
    item_metadata TEXT,
    played_at TIMESTAMP NOT NULL,
    duration_secs INTEGER,
    UNIQUE(source, user_id, item_id, played_at)
);

CREATE TABLE IF NOT EXISTS poll_state (
    source TEXT PRIMARY KEY,
    last_poll TIMESTAMP,
    last_backfill TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_map (
    username TEXT NOT NULL,
    source TEXT NOT NULL,
    source_user_id TEXT NOT NULL,
    PRIMARY KEY (username, source)
);

CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id, source);
CREATE INDEX IF NOT EXISTS idx_events_played ON events(played_at);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)


def insert_event(conn, user_id, source, item_type, item_id, item_name,
                 metadata, played_at, duration_secs=None):
    try:
        conn.execute(
            """INSERT OR IGNORE INTO events
               (user_id, source, item_type, item_id, item_name,
                item_metadata, played_at, duration_secs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, source, item_type, item_id, item_name,
             json.dumps(metadata) if metadata else None,
             played_at, duration_secs)
        )
    except sqlite3.IntegrityError:
        pass


def get_poll_state(conn, source):
    row = conn.execute(
        "SELECT last_poll, last_backfill FROM poll_state WHERE source = ?",
        (source,)
    ).fetchone()
    return dict(row) if row else None


def set_poll_state(conn, source, last_poll=None, last_backfill=None):
    existing = get_poll_state(conn, source)
    if existing:
        if last_poll:
            conn.execute("UPDATE poll_state SET last_poll = ? WHERE source = ?",
                         (last_poll, source))
        if last_backfill:
            conn.execute("UPDATE poll_state SET last_backfill = ? WHERE source = ?",
                         (last_backfill, source))
    else:
        conn.execute(
            "INSERT INTO poll_state (source, last_poll, last_backfill) VALUES (?, ?, ?)",
            (source, last_poll, last_backfill)
        )


def get_user_map(conn, username=None, source=None):
    if username and source:
        row = conn.execute(
            "SELECT source_user_id FROM user_map WHERE username = ? AND source = ?",
            (username, source)
        ).fetchone()
        return row["source_user_id"] if row else None
    if source:
        return {r["source_user_id"]: r["username"]
                for r in conn.execute(
                    "SELECT username, source_user_id FROM user_map WHERE source = ?",
                    (source,)
                ).fetchall()}
    return conn.execute("SELECT * FROM user_map").fetchall()


def set_user_map(conn, username, source, source_user_id):
    conn.execute(
        """INSERT OR REPLACE INTO user_map (username, source, source_user_id)
           VALUES (?, ?, ?)""",
        (username, source, source_user_id)
    )


def reverse_user_map(conn, source):
    """source_user_id -> username"""
    return {r["source_user_id"]: r["username"]
            for r in conn.execute(
                "SELECT username, source_user_id FROM user_map WHERE source = ?",
                (source,)
            ).fetchall()}


# ── Query helpers ──

def get_dashboard_stats(conn, username):
    stats = {}
    row = conn.execute(
        """SELECT COALESCE(SUM(duration_secs), 0) as total_secs,
                  COUNT(*) as count
           FROM events WHERE user_id = ? AND source = 'jellyfin'""",
        (username,)
    ).fetchone()
    stats["watch_time_secs"] = row["total_secs"]
    stats["watch_count"] = row["count"]

    row = conn.execute(
        "SELECT COUNT(*) as count FROM events WHERE user_id = ? AND source = 'navidrome'",
        (username,)
    ).fetchone()
    stats["songs_played"] = row["count"]

    row = conn.execute(
        "SELECT COUNT(DISTINCT item_id) as count FROM events WHERE user_id = ? AND source = 'romm'",
        (username,)
    ).fetchone()
    stats["games_touched"] = row["count"]

    row = conn.execute(
        """SELECT COUNT(DISTINCT item_id) as count,
                  COALESCE(SUM(duration_secs), 0) as total_secs
           FROM events WHERE user_id = ? AND source = 'booklore'""",
        (username,)
    ).fetchone()
    stats["books_read"] = row["count"]
    stats["reading_time_secs"] = row["total_secs"]

    for source in ("jellyfin", "navidrome", "romm", "booklore"):
        recent = conn.execute(
            """SELECT item_name, item_type, played_at FROM events
               WHERE user_id = ? AND source = ?
               ORDER BY played_at DESC LIMIT 3""",
            (username, source)
        ).fetchall()
        stats[f"recent_{source}"] = [dict(r) for r in recent]

    return stats


def get_wrapped_stats(conn, username, year=None):
    if year is None:
        year = datetime.now().year
    start = f"{year}-01-01"
    end = f"{year + 1}-01-01"

    stats = {}

    # Top movies/shows
    stats["top_video"] = [dict(r) for r in conn.execute(
        """SELECT item_name, item_type, COUNT(*) as plays,
                  COALESCE(SUM(duration_secs), 0) as total_secs,
                  item_metadata
           FROM events
           WHERE user_id = ? AND source = 'jellyfin'
             AND played_at >= ? AND played_at < ?
           GROUP BY item_id
           ORDER BY plays DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Top songs
    stats["top_songs"] = [dict(r) for r in conn.execute(
        """SELECT item_name, COUNT(*) as plays, item_metadata
           FROM events
           WHERE user_id = ? AND source = 'navidrome' AND item_type = 'song'
             AND played_at >= ? AND played_at < ?
           GROUP BY item_id
           ORDER BY plays DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Top artists (from metadata)
    stats["top_artists"] = [dict(r) for r in conn.execute(
        """SELECT json_extract(item_metadata, '$.artist') as artist,
                  COUNT(*) as plays
           FROM events
           WHERE user_id = ? AND source = 'navidrome' AND item_type = 'song'
             AND played_at >= ? AND played_at < ?
             AND artist IS NOT NULL
           GROUP BY artist
           ORDER BY plays DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Top albums
    stats["top_albums"] = [dict(r) for r in conn.execute(
        """SELECT json_extract(item_metadata, '$.album') as album,
                  json_extract(item_metadata, '$.artist') as artist,
                  COUNT(*) as plays
           FROM events
           WHERE user_id = ? AND source = 'navidrome' AND item_type = 'song'
             AND played_at >= ? AND played_at < ?
             AND album IS NOT NULL
           GROUP BY album
           ORDER BY plays DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Games
    stats["games"] = [dict(r) for r in conn.execute(
        """SELECT item_name, item_metadata, COUNT(*) as plays
           FROM events
           WHERE user_id = ? AND source = 'romm'
             AND played_at >= ? AND played_at < ?
           GROUP BY item_id
           ORDER BY plays DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Genre breakdown (video)
    stats["video_genres"] = [dict(r) for r in conn.execute(
        """SELECT json_extract(item_metadata, '$.genre') as genre,
                  COUNT(*) as count
           FROM events
           WHERE user_id = ? AND source = 'jellyfin'
             AND played_at >= ? AND played_at < ?
             AND genre IS NOT NULL
           GROUP BY genre
           ORDER BY count DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Genre breakdown (music)
    stats["music_genres"] = [dict(r) for r in conn.execute(
        """SELECT json_extract(item_metadata, '$.genre') as genre,
                  COUNT(*) as count
           FROM events
           WHERE user_id = ? AND source = 'navidrome'
             AND played_at >= ? AND played_at < ?
             AND genre IS NOT NULL
           GROUP BY genre
           ORDER BY count DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Monthly activity
    stats["monthly"] = [dict(r) for r in conn.execute(
        """SELECT strftime('%m', played_at) as month,
                  source, COUNT(*) as count
           FROM events
           WHERE user_id = ? AND played_at >= ? AND played_at < ?
           GROUP BY month, source
           ORDER BY month""",
        (username, start, end)
    ).fetchall()]

    # Most active day
    stats["busiest_day"] = conn.execute(
        """SELECT date(played_at) as day, COUNT(*) as count
           FROM events
           WHERE user_id = ? AND played_at >= ? AND played_at < ?
           GROUP BY day ORDER BY count DESC LIMIT 1""",
        (username, start, end)
    ).fetchone()
    if stats["busiest_day"]:
        stats["busiest_day"] = dict(stats["busiest_day"])

    # Total watch time this year
    row = conn.execute(
        """SELECT COALESCE(SUM(duration_secs), 0) as total
           FROM events
           WHERE user_id = ? AND source = 'jellyfin'
             AND played_at >= ? AND played_at < ?""",
        (username, start, end)
    ).fetchone()
    stats["year_watch_secs"] = row["total"]

    # Total songs this year
    row = conn.execute(
        """SELECT COUNT(*) as total
           FROM events
           WHERE user_id = ? AND source = 'navidrome'
             AND played_at >= ? AND played_at < ?""",
        (username, start, end)
    ).fetchone()
    stats["year_songs"] = row["total"]

    # Top books
    stats["top_books"] = [dict(r) for r in conn.execute(
        """SELECT item_name, COUNT(*) as sessions,
                  COALESCE(SUM(duration_secs), 0) as total_secs,
                  item_metadata
           FROM events
           WHERE user_id = ? AND source = 'booklore'
             AND played_at >= ? AND played_at < ?
           GROUP BY item_id
           ORDER BY total_secs DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Top book authors
    stats["top_book_authors"] = [dict(r) for r in conn.execute(
        """SELECT json_extract(item_metadata, '$.author') as author,
                  COUNT(*) as sessions,
                  COALESCE(SUM(duration_secs), 0) as total_secs
           FROM events
           WHERE user_id = ? AND source = 'booklore'
             AND played_at >= ? AND played_at < ?
             AND author IS NOT NULL
           GROUP BY author
           ORDER BY total_secs DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Book genres
    stats["book_genres"] = [dict(r) for r in conn.execute(
        """SELECT json_extract(item_metadata, '$.genre') as genre,
                  COUNT(*) as count
           FROM events
           WHERE user_id = ? AND source = 'booklore'
             AND played_at >= ? AND played_at < ?
             AND genre IS NOT NULL
           GROUP BY genre
           ORDER BY count DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    # Total reading time this year
    row = conn.execute(
        """SELECT COALESCE(SUM(duration_secs), 0) as total,
                  COUNT(DISTINCT item_id) as books
           FROM events
           WHERE user_id = ? AND source = 'booklore'
             AND played_at >= ? AND played_at < ?""",
        (username, start, end)
    ).fetchone()
    stats["year_reading_secs"] = row["total"]
    stats["year_books"] = row["books"]

    # Game platforms
    stats["game_platforms"] = [dict(r) for r in conn.execute(
        """SELECT json_extract(item_metadata, '$.platform') as platform,
                  COUNT(DISTINCT item_id) as count
           FROM events
           WHERE user_id = ? AND source = 'romm'
             AND played_at >= ? AND played_at < ?
             AND platform IS NOT NULL
           GROUP BY platform
           ORDER BY count DESC LIMIT 10""",
        (username, start, end)
    ).fetchall()]

    return stats


def get_history(conn, username, source=None, item_type=None,
                offset=0, limit=50):
    query = "SELECT * FROM events WHERE user_id = ?"
    params = [username]
    if source:
        query += " AND source = ?"
        params.append(source)
    if item_type:
        query += " AND item_type = ?"
        params.append(item_type)
    query += " ORDER BY played_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return [dict(r) for r in conn.execute(query, params).fetchall()]
