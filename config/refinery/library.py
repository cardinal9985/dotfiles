"""Library awareness layer. Reads Navidrome's existing index (it already
scans the music folder), and cross-references against MusicBrainz to find
missing albums per artist."""

import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import music  # for _http_get, MB_BASE

log = logging.getLogger("refinery.library")

NAVIDROME_DB = os.environ.get("NAVIDROME_DB", "/var/lib/navidrome/navidrome.db")
MUSIC_ROOT   = os.environ.get("REFINERY_MUSIC_TARGET", "/mnt/storage/media/music")
MB_ARTIST_CACHE = os.environ.get("REFINERY_MB_ARTIST_CACHE",
                                 "/persist/refinery/mb_artists")
MB_DISCO_CACHE  = os.environ.get("REFINERY_MB_DISCO_CACHE",
                                 "/persist/refinery/mb_discography")
DISCO_TTL_SECS  = 7 * 86400   # 1 week - refresh weekly so new releases land


def _norm(s):
    """Light normalization for fuzzy album-title comparison: lowercase,
    strip diacritics and punctuation, collapse whitespace."""
    if not s:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", s)   # drop (Live), [Remaster]
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


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
    """All ALBUM-type release groups from MusicBrainz. Cached to disk for
    one week so the radar can iterate every library artist quickly."""
    mbid = _mb_artist_id(artist_name)
    if not mbid:
        return []

    os.makedirs(MB_DISCO_CACHE, exist_ok=True)
    cache_path = os.path.join(MB_DISCO_CACHE, f"{mbid}.json")
    if os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < DISCO_TTL_SECS:
            try:
                with open(cache_path) as f:
                    return json.load(f)
            except Exception:
                pass

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
    result = [{
        "title":              g.get("title"),
        "first_release_date": g.get("first-release-date") or "",
        "primary_type":       g.get("primary-type"),
        "secondary_types":    g.get("secondary-types") or [],
        "mbid":               g.get("id"),
    } for g in groups if g.get("title")]

    try:
        with open(cache_path, "w") as f:
            json.dump(result, f)
    except Exception:
        pass
    return result


def radar(days=180, include_upcoming=True):
    """Cross-artist release radar. For every artist in the library, return
    release-groups dated within the last `days` (and optionally in the
    future) that we don't already own. Sorted newest first."""
    today  = datetime.now().date()
    cutoff = today - timedelta(days=days)
    out    = []
    artists = list_artists()
    log.info("radar: scanning %d library artists (cutoff=%s)",
             len(artists), cutoff)
    for a in artists:
        name = a["name"]
        try:
            owned = {_norm(x["title"]) for x in albums_for(name)}
            for rg in discography(name):
                date = rg.get("first_release_date") or ""
                if not date:
                    continue
                # MB dates can be YYYY or YYYY-MM - pad to a real date.
                try:
                    parts = [int(p) for p in date.split("-")]
                    while len(parts) < 3:
                        parts.append(1)
                    rdate = datetime(*parts[:3]).date()
                except Exception:
                    continue
                if rdate < cutoff:
                    continue
                if rdate > today and not include_upcoming:
                    continue
                if any(t in {"Live", "Compilation", "Soundtrack", "Demo",
                             "Interview", "Spokenword"}
                       for t in (rg.get("secondary_types") or [])):
                    continue
                if _norm(rg["title"]) in owned:
                    continue
                out.append({
                    "artist":             name,
                    "title":              rg["title"],
                    "first_release_date": date,
                    "primary_type":       rg.get("primary_type"),
                    "mbid":               rg.get("mbid"),
                    "upcoming":           rdate > today,
                })
        except Exception as e:
            log.warning("radar: failed for %s: %s", name, e)
    return sorted(out, key=lambda x: x["first_release_date"], reverse=True)


def missing_albums(artist_name):
    """Release groups in MB discography that aren't in the local library
    (fuzzy match on normalized title)."""
    owned_titles = {_norm(a["title"]) for a in albums_for(artist_name)}
    out = []
    for rg in discography(artist_name):
        # Skip live/compilation/soundtrack secondary types - usually noisy
        if any(t in {"Live", "Compilation", "Soundtrack", "Demo",
                     "Interview", "Spokenword"}
               for t in (rg.get("secondary_types") or [])):
            continue
        if _norm(rg["title"]) not in owned_titles:
            out.append(rg)
    return sorted(out, key=lambda x: x.get("first_release_date") or "")
