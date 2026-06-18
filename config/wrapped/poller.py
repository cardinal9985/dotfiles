import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta

import pymysql
import pymysql.cursors
import requests

from db import get_db, insert_event, get_poll_state, set_poll_state, \
    set_user_map, reverse_user_map

log = logging.getLogger("wrapped.poller")


def _secret(name):
    path = os.environ.get(name + "_FILE")
    if path:
        try:
            with open(path) as f:
                return f.read().strip()
        except FileNotFoundError:
            log.warning("Secret file not found: %s", path)
    return os.environ.get(name) or None


JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://host.containers.internal:63072")
JELLYFIN_API_KEY = _secret("JELLYFIN_API_KEY")
ROMM_URL = os.environ.get("ROMM_URL", "http://host.containers.internal:8998")
BOOKLORE_DB_HOST = os.environ.get("BOOKLORE_DB_HOST", "10.89.13.2")
BOOKLORE_DB_PORT = int(os.environ.get("BOOKLORE_DB_PORT", "3306"))
BOOKLORE_DB_NAME = os.environ.get("BOOKLORE_DB_NAME", "booklore")
BOOKLORE_DB_USER = os.environ.get("BOOKLORE_DB_USER", "booklore")
BOOKLORE_DB_PASSWORD = _secret("BOOKLORE_DB_PASSWORD")
NAVIDROME_DB = os.environ.get("NAVIDROME_DB", "/navidrome.db")


# ── Jellyfin ──────────────────────────────────────────────────────────────────

def _jellyfin_headers():
    return {"X-Emby-Token": JELLYFIN_API_KEY}


def _jellyfin_discover_users(conn):
    if not JELLYFIN_API_KEY:
        return
    try:
        resp = requests.get(f"{JELLYFIN_URL}/Users",
                            headers=_jellyfin_headers(), timeout=10)
        resp.raise_for_status()
        for user in resp.json():
            username = user["Name"].lower()
            set_user_map(conn, username, "jellyfin", user["Id"])
            log.info("Mapped Jellyfin user: %s -> %s", username, user["Id"])
    except Exception as e:
        log.error("Jellyfin user discovery failed: %s", e)


def _type_from_jellyfin(item_type):
    mapping = {"Movie": "movie", "Episode": "episode", "Audio": "song"}
    return mapping.get(item_type, item_type.lower() if item_type else "unknown")


def poll_jellyfin():
    if not JELLYFIN_API_KEY:
        log.warning("No Jellyfin API key, skipping")
        return

    with get_db() as conn:
        state = get_poll_state(conn, "jellyfin")

        # Auto-discover users on first run
        if not state:
            _jellyfin_discover_users(conn)

        user_map = reverse_user_map(conn, "jellyfin")
        if not user_map:
            _jellyfin_discover_users(conn)
            user_map = reverse_user_map(conn, "jellyfin")
        if not user_map:
            log.warning("No Jellyfin users mapped")
            return

        # Backfill on first run
        if not state or not state.get("last_backfill"):
            log.info("Running Jellyfin backfill...")
            _jellyfin_backfill(conn, user_map)
            set_poll_state(conn, "jellyfin",
                           last_backfill=datetime.utcnow().isoformat(),
                           last_poll=datetime.utcnow().isoformat())
            return

        # Incremental poll via Playback Reporting
        since = state["last_poll"] or (datetime.utcnow() - timedelta(hours=1)).isoformat()
        now = datetime.utcnow().isoformat()
        _jellyfin_poll_since(conn, user_map, since)
        set_poll_state(conn, "jellyfin", last_poll=now)


def _jellyfin_backfill(conn, user_map):
    """Import all history via custom SQL query against Playback Reporting DB."""
    # Reverse map: jellyfin user ID -> username
    id_to_name = user_map  # already jf_id -> username

    try:
        resp = requests.post(
            f"{JELLYFIN_URL}/user_usage_stats/submit_custom_query",
            headers=_jellyfin_headers(),
            json={
                "CustomQueryString": "SELECT DateCreated, UserId, ItemId, ItemType, ItemName, PlayDuration, PlaybackMethod, ClientName, DeviceName FROM PlaybackActivity ORDER BY DateCreated",
                "ReplaceUserId": False
            },
            timeout=60
        )
        if resp.status_code == 404:
            log.warning("Playback Reporting plugin not installed")
            return
        resp.raise_for_status()
        data = resp.json()

        columns = data.get("colums", data.get("columns", []))
        results = data.get("results", [])

        if not columns or not results:
            log.warning("Jellyfin backfill: empty response (columns=%s, rows=%d)",
                        columns, len(results))
            return

        # Build column index
        col_idx = {col.lower(): i for i, col in enumerate(columns)}
        count = 0
        for row_data in results:
            user_id = row_data[col_idx.get("userid", -1)] if "userid" in col_idx else None
            username = id_to_name.get(user_id)
            if not username:
                continue

            item_name = row_data[col_idx.get("itemname", -1)] if "itemname" in col_idx else "Unknown"
            item_id = row_data[col_idx.get("itemid", -1)] if "itemid" in col_idx else item_name
            item_type = _type_from_jellyfin(
                row_data[col_idx.get("itemtype", -1)] if "itemtype" in col_idx else ""
            )
            played_at = row_data[col_idx.get("datecreated", -1)] if "datecreated" in col_idx else None
            duration = row_data[col_idx.get("playduration", -1)] if "playduration" in col_idx else None

            if isinstance(duration, str):
                try:
                    duration = int(float(duration))
                except (ValueError, TypeError):
                    duration = None
            elif isinstance(duration, (int, float)):
                duration = int(duration)

            metadata = {}
            if "playbackmethod" in col_idx:
                metadata["playmethod"] = row_data[col_idx["playbackmethod"]]
            if "clientname" in col_idx:
                metadata["client"] = row_data[col_idx["clientname"]]

            if played_at:
                insert_event(conn, username, "jellyfin", item_type, str(item_id),
                             str(item_name), metadata, played_at, duration)
                count += 1

        log.info("Jellyfin backfill: %d events total", count)
    except Exception as e:
        log.error("Jellyfin backfill error: %s", e)


def _jellyfin_poll_since(conn, user_map, since):
    """Poll per-user per-date for new play events."""
    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00") if "Z" in since else since)
    if since_dt.tzinfo:
        since_dt = since_dt.replace(tzinfo=None)
    now = datetime.utcnow()

    for jf_user_id, username in user_map.items():
        current = since_dt.date()
        while current <= now.date():
            date_str = current.isoformat()
            try:
                resp = requests.get(
                    f"{JELLYFIN_URL}/user_usage_stats/{jf_user_id}/{date_str}/GetItems",
                    headers=_jellyfin_headers(),
                    timeout=15
                )
                if resp.status_code == 404:
                    current += timedelta(days=1)
                    continue
                resp.raise_for_status()
                items = resp.json()
                for item in items:
                    row = {
                        "Name": item.get("Name"),
                        "Id": item.get("Id"),
                        "Type": item.get("Type"),
                        "Date": f"{date_str} {item.get('Time', '00:00')}",
                        "Duration": item.get("Duration"),
                        "PlayMethod": item.get("Method"),
                    }
                    _insert_jellyfin_event(conn, username, row)
            except Exception as e:
                log.error("Jellyfin poll error for %s on %s: %s", username, date_str, e)
            current += timedelta(days=1)


def _insert_jellyfin_event(conn, username, row):
    item_name = row.get("Name") or row.get("ItemName") or "Unknown"
    item_id = row.get("ItemId") or row.get("Id") or item_name
    item_type = _type_from_jellyfin(row.get("Type") or row.get("ItemType") or "")
    played_at = row.get("Date") or row.get("date") or row.get("DateCreated")
    duration = row.get("PlayDuration") or row.get("Duration")
    if isinstance(duration, str):
        try:
            parts = duration.split(":")
            duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
        except (ValueError, IndexError):
            duration = None

    metadata = {}
    for key in ("SeriesName", "Genre", "Year", "PlayMethod"):
        val = row.get(key) or row.get(key.lower())
        if val:
            metadata[key.lower().replace("seriesname", "series")] = val

    if played_at:
        insert_event(conn, username, "jellyfin", item_type, str(item_id),
                     item_name, metadata, played_at, duration)


# ── Navidrome ─────────────────────────────────────────────────────────────────

def _navidrome_discover_users(conn, nd_conn):
    try:
        rows = nd_conn.execute("SELECT id, user_name FROM user").fetchall()
        for row in rows:
            username = row["user_name"].lower()
            set_user_map(conn, username, "navidrome", row["id"])
            log.info("Mapped Navidrome user: %s -> %s", username, row["id"])
    except Exception as e:
        log.error("Navidrome user discovery failed: %s", e)


def poll_navidrome():
    if not os.path.exists(NAVIDROME_DB):
        log.warning("Navidrome DB not found at %s", NAVIDROME_DB)
        return

    nd_conn = sqlite3.connect(f"file:{NAVIDROME_DB}?mode=ro", uri=True)
    nd_conn.row_factory = sqlite3.Row

    try:
        with get_db() as conn:
            state = get_poll_state(conn, "navidrome")

            if not state:
                _navidrome_discover_users(conn, nd_conn)

            user_map = reverse_user_map(conn, "navidrome")
            if not user_map:
                _navidrome_discover_users(conn, nd_conn)
                user_map = reverse_user_map(conn, "navidrome")
            if not user_map:
                log.warning("No Navidrome users mapped")
                return

            if not state or not state.get("last_backfill"):
                log.info("Running Navidrome backfill...")
                _navidrome_backfill(conn, nd_conn, user_map)
                set_poll_state(conn, "navidrome",
                               last_backfill=datetime.utcnow().isoformat(),
                               last_poll=datetime.utcnow().isoformat())
                return

            since = state["last_poll"]
            now = datetime.utcnow().isoformat()
            _navidrome_poll_since(conn, nd_conn, user_map, since)
            set_poll_state(conn, "navidrome", last_poll=now)
    finally:
        nd_conn.close()


def _navidrome_backfill(conn, nd_conn, user_map):
    """Import all annotation play data from Navidrome."""
    for nd_user_id, username in user_map.items():
        try:
            rows = nd_conn.execute(
                """SELECT a.item_id, a.item_type, a.play_count, a.play_date,
                          COALESCE(mf.title, a.item_id) as title,
                          mf.artist, mf.album, mf.genre,
                          mf.album_artist
                   FROM annotation a
                   JOIN media_file mf ON a.item_id = mf.id
                   WHERE a.user_id = ? AND a.item_type = 'media_file' AND a.play_count > 0""",
                (nd_user_id,)
            ).fetchall()
            count = 0
            for row in rows:
                play_date = row["play_date"]
                if not play_date:
                    continue
                metadata = {}
                for key in ("artist", "album", "genre", "album_artist"):
                    if row[key]:
                        metadata[key] = row[key]
                # Navidrome only stores last play date + count, not individual timestamps.
                # Insert one event at the last play date per item.
                insert_event(conn, username, "navidrome", "song",
                             row["item_id"], row["title"], metadata,
                             play_date, None)
                count += 1
            log.info("Navidrome backfill for %s: %d items", username, count)
        except Exception as e:
            log.error("Navidrome backfill error for %s: %s", username, e)


def _navidrome_poll_since(conn, nd_conn, user_map, since):
    """Check for annotation changes since last poll."""
    for nd_user_id, username in user_map.items():
        try:
            rows = nd_conn.execute(
                """SELECT a.item_id, a.item_type, a.play_count, a.play_date,
                          COALESCE(mf.title, a.item_id) as title,
                          mf.artist, mf.album, mf.genre, mf.album_artist
                   FROM annotation a
                   JOIN media_file mf ON a.item_id = mf.id
                   WHERE a.user_id = ? AND a.item_type = 'media_file' AND a.play_date > ?""",
                (nd_user_id, since)
            ).fetchall()
            for row in rows:
                if not row["play_date"]:
                    continue
                metadata = {}
                for key in ("artist", "album", "genre", "album_artist"):
                    if row[key]:
                        metadata[key] = row[key]
                insert_event(conn, username, "navidrome", "song",
                             row["item_id"], row["title"], metadata,
                             row["play_date"], None)
        except Exception as e:
            log.error("Navidrome poll error for %s: %s", username, e)


# ── RomM ──────────────────────────────────────────────────────────────────────

ROMM_DB_HOST = os.environ.get("ROMM_DB_HOST", "host.containers.internal")
ROMM_DB_PORT = int(os.environ.get("ROMM_DB_PORT", "3308"))
ROMM_DB_NAME = os.environ.get("ROMM_DB_NAME", "romm")
ROMM_DB_USER = os.environ.get("ROMM_DB_USER", "romm")
ROMM_DB_PASSWORD = _secret("ROMM_DB_PASSWORD")


def _romm_connect():
    if not ROMM_DB_PASSWORD:
        log.warning("No RomM DB password, skipping")
        return None
    try:
        return pymysql.connect(
            host=ROMM_DB_HOST,
            port=ROMM_DB_PORT,
            user=ROMM_DB_USER,
            password=ROMM_DB_PASSWORD,
            database=ROMM_DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            read_timeout=30,
        )
    except Exception as e:
        log.error("RomM DB connection failed: %s", e)
        return None


def _romm_discover_users(conn, rm_conn):
    try:
        with rm_conn.cursor() as cur:
            cur.execute("SELECT id, username FROM users")
            for row in cur.fetchall():
                username = row["username"].lower()
                set_user_map(conn, username, "romm", str(row["id"]))
                log.info("Mapped RomM user: %s -> %s", username, row["id"])
    except Exception as e:
        log.error("RomM user discovery failed: %s", e)


def poll_romm():
    rm_conn = _romm_connect()
    if not rm_conn:
        return

    try:
        with get_db() as conn:
            state = get_poll_state(conn, "romm")

            if not state:
                _romm_discover_users(conn, rm_conn)

            user_map = reverse_user_map(conn, "romm")
            if not user_map:
                _romm_discover_users(conn, rm_conn)
                user_map = reverse_user_map(conn, "romm")
            if not user_map:
                log.warning("No RomM users mapped")
                return

            if not state or not state.get("last_backfill"):
                log.info("Running RomM backfill...")
                _romm_backfill(conn, rm_conn, user_map)
                set_poll_state(conn, "romm",
                               last_backfill=datetime.utcnow().isoformat(),
                               last_poll=datetime.utcnow().isoformat())
                return

            since = state["last_poll"]
            now = datetime.utcnow().isoformat()
            _romm_poll_since(conn, rm_conn, user_map, since)
            set_poll_state(conn, "romm", last_poll=now)
    finally:
        rm_conn.close()


def _romm_query_played(rm_conn, user_id, since=None):
    """Query rom_user joined with roms and platforms for played games."""
    query = """
        SELECT ru.rom_id, ru.last_played, ru.status, ru.completion,
               ru.now_playing, ru.updated_at,
               r.name AS rom_name, r.fs_name,
               p.name AS platform_name
        FROM rom_user ru
        JOIN roms r ON ru.rom_id = r.id
        JOIN platforms p ON r.platform_id = p.id
        WHERE ru.user_id = %s AND ru.last_played IS NOT NULL
    """
    params = [user_id]
    if since:
        query += " AND ru.updated_at > %s"
        params.append(since)
    query += " ORDER BY ru.last_played"

    with rm_conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def _romm_backfill(conn, rm_conn, user_map):
    for rm_user_id, username in user_map.items():
        try:
            rows = _romm_query_played(rm_conn, int(rm_user_id))
            count = 0
            for r in rows:
                rom_name = r["rom_name"] or r["fs_name"] or "Unknown"
                metadata = {
                    "platform": r["platform_name"],
                    "status": r["status"],
                    "completion": r["completion"],
                    "now_playing": r["now_playing"],
                }
                metadata = {k: v for k, v in metadata.items() if v}
                played_at = r["last_played"].isoformat() if hasattr(r["last_played"], "isoformat") else str(r["last_played"])
                insert_event(conn, username, "romm", "game",
                             str(r["rom_id"]), rom_name, metadata,
                             played_at, None)
                count += 1
            log.info("RomM backfill for %s: %d games", username, count)
        except Exception as e:
            log.error("RomM backfill error for %s: %s", username, e)


def _romm_poll_since(conn, rm_conn, user_map, since):
    for rm_user_id, username in user_map.items():
        try:
            rows = _romm_query_played(rm_conn, int(rm_user_id), since)
            for r in rows:
                rom_name = r["rom_name"] or r["fs_name"] or "Unknown"
                metadata = {
                    "platform": r["platform_name"],
                    "status": r["status"],
                    "completion": r["completion"],
                    "now_playing": r["now_playing"],
                }
                metadata = {k: v for k, v in metadata.items() if v}
                played_at = r["last_played"].isoformat() if hasattr(r["last_played"], "isoformat") else str(r["last_played"])
                insert_event(conn, username, "romm", "game",
                             str(r["rom_id"]), rom_name, metadata,
                             played_at, None)
        except Exception as e:
            log.error("RomM poll error for %s: %s", username, e)


# ── BookLore ──────────────────────────────────────────────────────────────────

def _booklore_connect():
    if not BOOKLORE_DB_PASSWORD:
        log.warning("No BookLore DB password, skipping")
        return None
    try:
        return pymysql.connect(
            host=BOOKLORE_DB_HOST,
            port=BOOKLORE_DB_PORT,
            user=BOOKLORE_DB_USER,
            password=BOOKLORE_DB_PASSWORD,
            database=BOOKLORE_DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            read_timeout=30,
        )
    except Exception as e:
        log.error("BookLore DB connection failed: %s", e)
        return None


def _booklore_discover_users(conn, bl_conn):
    try:
        with bl_conn.cursor() as cur:
            cur.execute("SELECT id, username FROM users")
            for row in cur.fetchall():
                username = row["username"].lower()
                set_user_map(conn, username, "booklore", str(row["id"]))
                log.info("Mapped BookLore user: %s -> %s", username, row["id"])
    except Exception as e:
        log.error("BookLore user discovery failed: %s", e)


def poll_booklore():
    bl_conn = _booklore_connect()
    if not bl_conn:
        return

    try:
        with get_db() as conn:
            state = get_poll_state(conn, "booklore")

            if not state:
                _booklore_discover_users(conn, bl_conn)

            user_map = reverse_user_map(conn, "booklore")
            if not user_map:
                _booklore_discover_users(conn, bl_conn)
                user_map = reverse_user_map(conn, "booklore")
            if not user_map:
                log.warning("No BookLore users mapped")
                return

            if not state or not state.get("last_backfill"):
                log.info("Running BookLore backfill...")
                _booklore_backfill(conn, bl_conn, user_map)
                set_poll_state(conn, "booklore",
                               last_backfill=datetime.utcnow().isoformat(),
                               last_poll=datetime.utcnow().isoformat())
                return

            since = state["last_poll"]
            now = datetime.utcnow().isoformat()
            _booklore_poll_since(conn, bl_conn, user_map, since)
            set_poll_state(conn, "booklore", last_poll=now)
    finally:
        bl_conn.close()


def _booklore_get_authors(bl_conn, book_id):
    with bl_conn.cursor() as cur:
        cur.execute("""
            SELECT a.name FROM author a
            JOIN book_metadata_author_mapping m ON a.id = m.author_id
            WHERE m.book_id = %s LIMIT 3
        """, (book_id,))
        return ", ".join(r["name"] for r in cur.fetchall())


def _booklore_get_categories(bl_conn, book_id):
    with bl_conn.cursor() as cur:
        cur.execute("""
            SELECT c.name FROM category c
            JOIN book_metadata_category_mapping m ON c.id = m.category_id
            WHERE m.book_id = %s LIMIT 3
        """, (book_id,))
        return ", ".join(r["name"] for r in cur.fetchall())


def _booklore_query_progress(bl_conn, user_id, since=None):
    """Query user_book_progress with book metadata."""
    query = """
        SELECT ubp.book_id, ubp.last_read_time, ubp.read_status,
               ubp.pdf_progress_percent, ubp.epub_progress_percent,
               ubp.cbx_progress_percent,
               bm.title, bm.series_name, bm.publisher
        FROM user_book_progress ubp
        JOIN book_metadata bm ON ubp.book_id = bm.book_id
        WHERE ubp.user_id = %s AND ubp.last_read_time IS NOT NULL
    """
    params = [user_id]
    if since:
        query += " AND ubp.last_read_time > %s"
        params.append(since)
    query += " ORDER BY ubp.last_read_time"

    with bl_conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def _booklore_backfill(conn, bl_conn, user_map):
    for bl_user_id, username in user_map.items():
        try:
            rows = _booklore_query_progress(bl_conn, int(bl_user_id))
            count = 0
            for r in rows:
                authors = _booklore_get_authors(bl_conn, r["book_id"])
                categories = _booklore_get_categories(bl_conn, r["book_id"])
                progress = r["pdf_progress_percent"] or r["epub_progress_percent"] or r["cbx_progress_percent"] or 0
                metadata = {
                    "author": authors,
                    "genre": categories,
                    "series": r["series_name"],
                    "publisher": r["publisher"],
                    "status": r["read_status"],
                    "progress": round(progress, 1),
                }
                metadata = {k: v for k, v in metadata.items() if v}
                played_at = r["last_read_time"].isoformat() if hasattr(r["last_read_time"], "isoformat") else str(r["last_read_time"])
                insert_event(conn, username, "booklore", "book",
                             str(r["book_id"]), r["title"], metadata,
                             played_at, None)
                count += 1
            log.info("BookLore backfill for %s: %d books", username, count)
        except Exception as e:
            log.error("BookLore backfill error for %s: %s", username, e)


def _booklore_poll_since(conn, bl_conn, user_map, since):
    for bl_user_id, username in user_map.items():
        try:
            rows = _booklore_query_progress(bl_conn, int(bl_user_id), since)
            for r in rows:
                authors = _booklore_get_authors(bl_conn, r["book_id"])
                categories = _booklore_get_categories(bl_conn, r["book_id"])
                progress = r["pdf_progress_percent"] or r["epub_progress_percent"] or r["cbx_progress_percent"] or 0
                metadata = {
                    "author": authors,
                    "genre": categories,
                    "series": r["series_name"],
                    "publisher": r["publisher"],
                    "status": r["read_status"],
                    "progress": round(progress, 1),
                }
                metadata = {k: v for k, v in metadata.items() if v}
                played_at = r["last_read_time"].isoformat() if hasattr(r["last_read_time"], "isoformat") else str(r["last_read_time"])
                insert_event(conn, username, "booklore", "book",
                             str(r["book_id"]), r["title"], metadata,
                             played_at, None)
        except Exception as e:
            log.error("BookLore poll error for %s: %s", username, e)
