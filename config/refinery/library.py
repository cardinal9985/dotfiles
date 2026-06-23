"""Library awareness layer. Reads Navidrome's existing index (it already
scans the music folder), and cross-references against MusicBrainz to find
missing albums per artist."""

import logging
import os
import re
import sqlite3
from pathlib import Path

import music  # for _http_get, _norm, MB_BASE

log = logging.getLogger("refinery.library")

NAVIDROME_DB = os.environ.get("NAVIDROME_DB", "/var/lib/navidrome/navidrome.db")
MUSIC_ROOT   = os.environ.get("REFINERY_MUSIC_TARGET", "/mnt/storage/media/music")
MB_ARTIST_CACHE = os.environ.get("REFINERY_MB_ARTIST_CACHE",
                                 "/persist/refinery/mb_artists")


def _nd():
    return sqlite3.connect(f"file:{NAVIDROME_DB}?mode=ro", uri=True)


def list_artists():
    """All album-artists in the library with album/track counts."""
    try:
        nd = _nd()
        nd.row_factory = sqlite3.Row
        try:
            rows = nd.execute("""
                SELECT album_artist AS name,
                       COUNT(DISTINCT album_id) AS albums,
                       COUNT(*) AS tracks
                FROM media_file
                WHERE album_artist IS NOT NULL AND album_artist != ''
                GROUP BY album_artist
                ORDER BY album_artist COLLATE NOCASE
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            nd.close()
    except Exception as e:
        log.warning("list_artists failed: %s", e)
        return []


def albums_for(artist):
    """Albums in the library for a given album_artist, with folder path."""
    try:
        nd = _nd()
        nd.row_factory = sqlite3.Row
        try:
            rows = nd.execute("""
                SELECT album AS title, MAX(year) AS year,
                       MIN(path) AS sample_path, COUNT(*) AS track_count
                FROM media_file
                WHERE album_artist = ? AND album != ''
                GROUP BY album
                ORDER BY year, album
            """, (artist,)).fetchall()
        finally:
            nd.close()
    except Exception as e:
        log.warning("albums_for(%s) failed: %s", artist, e)
        return []
    out = []
    for r in rows:
        sample = r["sample_path"] or ""
        folder = os.path.dirname(sample) if sample else None
        out.append({
            "title":       r["title"],
            "year":        r["year"],
            "folder":      folder,
            "track_count": r["track_count"],
        })
    return out


def _mb_artist_id(name):
    """Resolve artist name to MusicBrainz MBID. Disk-cached forever."""
    if not name:
        return None
    os.makedirs(MB_ARTIST_CACHE, exist_ok=True)
    slug = re.sub(r"[^\w]+", "_", name.lower()).strip("_")[:80] or "unknown"
    cache = os.path.join(MB_ARTIST_CACHE, f"{slug}.txt")
    if os.path.exists(cache):
        try:
            return open(cache).read().strip() or None
        except Exception:
            pass
    r = music._http_get(f"{music.MB_BASE}/artist/", params={
        "query": name, "fmt": "json", "limit": 1,
    })
    if not r:
        return None
    try:
        artists = (r.json() or {}).get("artists") or []
        mbid = artists[0]["id"] if artists else ""
    except Exception:
        mbid = ""
    try:
        with open(cache, "w") as f:
            f.write(mbid)
    except Exception:
        pass
    return mbid or None


def discography(artist_name):
    """All ALBUM-type release groups from MusicBrainz. Singles/EPs excluded
    to keep the list focused."""
    mbid = _mb_artist_id(artist_name)
    if not mbid:
        return []
    r = music._http_get(f"{music.MB_BASE}/release-group", params={
        "artist": mbid,
        "type":   "album",
        "fmt":    "json",
        "limit":  100,
    })
    if not r:
        return []
    try:
        groups = (r.json() or {}).get("release-groups") or []
    except Exception:
        return []
    return [{
        "title":              g.get("title"),
        "first_release_date": g.get("first-release-date") or "",
        "primary_type":       g.get("primary-type"),
        "secondary_types":    g.get("secondary-types") or [],
        "mbid":               g.get("id"),
    } for g in groups if g.get("title")]


def missing_albums(artist_name):
    """Release groups in MB discography that aren't in the local library
    (fuzzy match on normalized title)."""
    owned_titles = {music._norm(a["title"]) for a in albums_for(artist_name)}
    out = []
    for rg in discography(artist_name):
        # Skip live/compilation/soundtrack secondary types - usually noisy
        if any(t in {"Live", "Compilation", "Soundtrack", "Demo",
                     "Interview", "Spokenword"}
               for t in (rg.get("secondary_types") or [])):
            continue
        if music._norm(rg["title"]) not in owned_titles:
            out.append(rg)
    return sorted(out, key=lambda x: x.get("first_release_date") or "")
