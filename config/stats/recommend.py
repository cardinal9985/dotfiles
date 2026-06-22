"""Movie recommendations via TMDB, seeded from the user's recent Jellyfin
movie events in the stats DB."""

import json
import logging
import os
import re
import unicodedata
from datetime import datetime

import requests as http

import db


_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE        = re.compile(r"\s+")
_PARENS_RE    = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
_FEAT_RE      = re.compile(r"\s+(feat\.?|ft\.?|featuring|with)\s+.*$", re.IGNORECASE)
_DASH_TAIL_RE = re.compile(r"\s+-\s+.*$")


def _norm(s):
    """Normalize artist/track/title for fuzzy comparison:
    - strip diacritics ("Beyoncé" -> "beyonce")
    - drop parenthesized/bracketed extras ("(Live)", "[Remastered]")
    - drop "feat./ft./with X" tails ("Artist feat. Other" -> "artist")
    - drop " - <qualifier>" tails (Last.fm style:
      'All My Loving - From "Across The Universe" Soundtrack',
      'Heroes - 1999 Digital Remaster',
      'Karma Police - Live at Wembley')
    - lowercase, strip punctuation, collapse whitespace
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = _PARENS_RE.sub("", s)
    s = _FEAT_RE.sub("", s)
    s = _DASH_TAIL_RE.sub("", s)
    s = _NON_ALNUM_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

log = logging.getLogger("stats.recommend")

TMDB_TOKEN = os.environ.get("TMDB_TOKEN", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w342"

LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "")
LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"

DEEZER_BASE = "https://api.deezer.com"

JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://127.0.0.1:8096")
JELLYFIN_API_KEY = os.environ.get("JELLYFIN_API_KEY", "")
NAVIDROME_DB = os.environ.get("NAVIDROME_DB", "/var/lib/navidrome/navidrome.db")

LIBRARY_TTL_SECS = 6 * 3600   # Refresh library snapshot every 6h

# Cache TTLs. Title->ID rarely changes, so we keep it ~30 days. Recommendations
# get refreshed weekly since TMDB tweaks their algorithm over time.
SEARCH_TTL_SECS = 30 * 86400
RECS_TTL_SECS   = 7 * 86400


def cache_is_warm():
    """Check that the library-aware cache has been built for the current code
    path. Looks for the Jellyfin library snapshot - that key only exists once
    the new build has run end-to-end."""
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM api_cache WHERE key = 'jellyfin:libraries' LIMIT 1"
        ).fetchone()
    return row is not None


def warm_cache_for(user):
    """Run all recommendation builds. Slow first time, fast after (cached)."""
    video_recommendations_by_library(user)
    music_recommendations(user)
    song_recommendations(user)


def _cache_get(key, max_age_secs):
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT value, fetched_at FROM api_cache WHERE key = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    try:
        age = (datetime.now() - datetime.fromisoformat(row["fetched_at"])).total_seconds()
    except Exception:
        return None
    if age > max_age_secs:
        return None
    try:
        return json.loads(row["value"])
    except Exception:
        return None


def _cache_set(key, value):
    with db.get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO api_cache (key, value, fetched_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), datetime.now().isoformat()),
        )


def _jellyfin_get(path, params=None):
    if not JELLYFIN_API_KEY:
        return None
    try:
        r = http.get(
            f"{JELLYFIN_URL}{path}",
            headers={"Authorization": f'MediaBrowser Token="{JELLYFIN_API_KEY}"'},
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("jellyfin error %s %s: %s", path, params, e)
        return None


def _jellyfin_libraries():
    """Return [{id, name, type}] for the user's media folders. Cached 6h."""
    key = "jellyfin:libraries"
    cached = _cache_get(key, LIBRARY_TTL_SECS)
    if cached is not None:
        return cached
    data = _jellyfin_get("/Library/MediaFolders") or {}
    libs = [{
        "id":   lib["Id"],
        "name": lib["Name"],
        "type": (lib.get("CollectionType") or "").lower(),
    } for lib in data.get("Items", []) if lib.get("CollectionType") in ("movies", "tvshows", "homevideos", "mixed", None)]
    _cache_set(key, libs)
    return libs


def _jellyfin_library_items(library_id):
    """Return [{id, name, type, tmdb_id}] for items in a library. Cached 6h."""
    key = f"jellyfin:items:{library_id}"
    cached = _cache_get(key, LIBRARY_TTL_SECS)
    if cached is not None:
        return cached
    data = _jellyfin_get("/Items", {
        "ParentId": library_id,
        "Recursive": "true",
        "IncludeItemTypes": "Movie,Series",
        "Fields": "ProviderIds",
        "Limit": 5000,
    }) or {}
    items = []
    for it in data.get("Items", []):
        items.append({
            "id":      it.get("Id"),
            "name":    it.get("Name"),
            "type":    it.get("Type"),
            "tmdb_id": (it.get("ProviderIds") or {}).get("Tmdb"),
        })
    _cache_set(key, items)
    return items


def _navidrome_existing_artists():
    """Set of normalized artist + album_artist names in the user's library."""
    key = "navidrome:existing_artists:v4"
    cached = _cache_get(key, LIBRARY_TTL_SECS)
    if cached is not None:
        return set(cached)
    try:
        import sqlite3 as sql
        nd_conn = sql.connect(f"file:{NAVIDROME_DB}?mode=ro", uri=True)
        try:
            rows = nd_conn.execute("""
                SELECT DISTINCT artist FROM media_file WHERE artist != ''
                UNION
                SELECT DISTINCT album_artist FROM media_file WHERE album_artist != ''
            """).fetchall()
        finally:
            nd_conn.close()
        names = sorted({_norm(r[0]) for r in rows if r[0]})
    except Exception as e:
        log.warning("navidrome artist scan failed: %s", e)
        names = []
    _cache_set(key, names)
    return set(names)


def _navidrome_existing_tracks():
    """Set of (normalized_artist, normalized_title) tuples in the library.
    Includes BOTH track artist and album_artist variants for each title so a
    Last.fm rec naming the album-artist still matches a track tagged with the
    featured artist (and vice-versa)."""
    key = "navidrome:existing_tracks:v4"
    cached = _cache_get(key, LIBRARY_TTL_SECS)
    if cached is not None:
        return {(p[0], p[1]) for p in cached}
    try:
        import sqlite3 as sql
        nd_conn = sql.connect(f"file:{NAVIDROME_DB}?mode=ro", uri=True)
        try:
            rows = nd_conn.execute("""
                SELECT artist, album_artist, title FROM media_file
                WHERE title != ''
            """).fetchall()
        finally:
            nd_conn.close()
        tracks = set()
        for artist, album_artist, title in rows:
            t = _norm(title)
            if not t:
                continue
            for a_field in (artist, album_artist):
                a = _norm(a_field) if a_field else ""
                if a:
                    tracks.add((a, t))
        tracks_list = sorted(tracks)
    except Exception as e:
        log.warning("navidrome track scan failed: %s", e)
        tracks_list = []
    _cache_set(key, tracks_list)
    return set(tracks_list)


def _tmdb_get(path, params=None):
    if not TMDB_TOKEN:
        return None
    try:
        r = http.get(
            f"{TMDB_BASE}{path}",
            headers={"Authorization": f"Bearer {TMDB_TOKEN}"},
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("TMDB error %s %s: %s", path, params, e)
        return None


def _search(kind, title):
    """kind is 'movie' or 'tv'. Returns TMDB id of first result. Cached."""
    key = f"tmdb:search:{kind}:{title}"
    cached = _cache_get(key, SEARCH_TTL_SECS)
    if cached is not None:
        # Cached miss is stored as null; treat as miss.
        return cached or None

    data = _tmdb_get(f"/search/{kind}", {"query": title})
    result = None
    if data and data.get("results"):
        result = data["results"][0]["id"]
    _cache_set(key, result)
    return result


def _recs(kind, tmdb_id, limit=8):
    key = f"tmdb:recs:{kind}:{tmdb_id}"
    cached = _cache_get(key, RECS_TTL_SECS)
    if cached is not None:
        return cached[:limit]

    data = _tmdb_get(f"/{kind}/{tmdb_id}/recommendations")
    results = data.get("results", []) if data else []
    _cache_set(key, results)
    return results[:limit]


def _parse_show_from_episode(name):
    """'Show Name - s01e01 - Episode Title' -> 'Show Name'."""
    if not name:
        return None
    for sep in (" - s", " - S"):
        if sep in name:
            return name.split(sep, 1)[0].strip()
    return None


def _seed_titles(user, limit=10):
    """Return list of (kind, title) seeds: movies + distinct TV show names."""
    with db.get_db() as conn:
        movies = conn.execute(
            """
            SELECT item_name, COUNT(*) AS plays
            FROM events
            WHERE user_id = ? AND source = 'jellyfin'
              AND LOWER(item_type) = 'movie'
              AND played_at > date('now', '-90 days')
            GROUP BY item_id
            ORDER BY plays DESC, MAX(played_at) DESC
            LIMIT ?
            """,
            (user, limit),
        ).fetchall()
        episodes = conn.execute(
            """
            SELECT item_name, played_at
            FROM events
            WHERE user_id = ? AND source = 'jellyfin'
              AND LOWER(item_type) = 'episode'
              AND played_at > date('now', '-90 days')
            ORDER BY played_at DESC
            """,
            (user,),
        ).fetchall()

    seeds = []
    for r in movies:
        if r["item_name"]:
            seeds.append(("movie", r["item_name"]))
    seen_shows = set()
    for r in episodes:
        show = _parse_show_from_episode(r["item_name"])
        if show and show not in seen_shows:
            seen_shows.add(show)
            seeds.append(("tv", show))
            if len(seen_shows) >= limit:
                break
    return seeds


def _normalize(kind, item, score):
    if kind == "movie":
        return {
            "kind": "movie",
            "tmdb_id": item.get("id"),
            "title": item.get("title", ""),
            "year": (item.get("release_date") or "")[:4],
            "overview": (item.get("overview") or "")[:240],
            "poster_url": f"{TMDB_IMG_BASE}{item['poster_path']}" if item.get("poster_path") else None,
            "request_type": "Movie",
            "score": score,
        }
    return {
        "kind": "tv",
        "tmdb_id": item.get("id"),
        "title": item.get("name", ""),
        "year": (item.get("first_air_date") or "")[:4],
        "overview": (item.get("overview") or "")[:240],
        "poster_url": f"{TMDB_IMG_BASE}{item['poster_path']}" if item.get("poster_path") else None,
        "request_type": "Show",
        "score": score,
    }


def video_recommendations_by_library(user, limit_per_lib=15):
    """Group video recommendations by Jellyfin library (Anime / Films / etc.).
    Dedupes against TMDB IDs already present in any of the user's libraries."""
    libraries = _jellyfin_libraries()
    if not libraries:
        return {}

    # Build lookup maps from the user's Jellyfin libraries.
    # - movie_item_to_lib: jellyfin movie item_id -> library name (events store
    #   the movie's own item_id, so direct lookup works for movies)
    # - show_name_to_lib: lowercase series name -> library name (events store
    #   the episode's item_id, NOT the series id, so we resolve via the show
    #   name we parse out of "Show - sNNeNN - Title")
    # - owned_tmdb: per-kind set for dedup against what the user already has
    movie_item_to_lib = {}
    show_name_to_lib  = {}
    owned_tmdb = {"movie": set(), "tv": set()}
    for lib in libraries:
        for it in _jellyfin_library_items(lib["id"]):
            it_type = it.get("type")
            it_id   = it.get("id")
            it_name = it.get("name")
            if it_type == "Movie" and it_id:
                movie_item_to_lib[it_id] = lib["name"]
            elif it_type == "Series" and it_name:
                show_name_to_lib[it_name.lower()] = lib["name"]
            tmdb = it.get("tmdb_id")
            if tmdb:
                try:
                    tmdb_int = int(tmdb)
                except (TypeError, ValueError):
                    continue
                if it_type == "Movie":
                    owned_tmdb["movie"].add(tmdb_int)
                elif it_type == "Series":
                    owned_tmdb["tv"].add(tmdb_int)

    # Pull user's recent video events.
    with db.get_db() as conn:
        rows = conn.execute(
            """
            SELECT item_id, item_name, item_type, played_at
            FROM events
            WHERE user_id = ? AND source = 'jellyfin'
              AND played_at > date('now', '-180 days')
              AND LOWER(item_type) IN ('movie', 'episode')
            ORDER BY played_at DESC
            """,
            (user,),
        ).fetchall()

    # Bucket seeds by library.
    seeds_by_lib = {}     # lib_name -> [(kind, title), ...]
    seen_by_lib  = {}     # lib_name -> set of (kind, title.lower())
    for row in rows:
        it_type = (row["item_type"] or "").lower()
        if it_type == "movie":
            lib_name = movie_item_to_lib.get(row["item_id"])
            kind, title = "movie", row["item_name"]
        elif it_type == "episode":
            title = _parse_show_from_episode(row["item_name"])
            if not title:
                continue
            lib_name = show_name_to_lib.get(title.lower())
            kind = "tv"
        else:
            continue
        if not lib_name:
            continue  # item no longer in any tracked library
        sig = (kind, title.lower())
        seen = seen_by_lib.setdefault(lib_name, set())
        if sig in seen:
            continue
        seen.add(sig)
        seeds_by_lib.setdefault(lib_name, []).append((kind, title))

    # Generate ranked recommendations per library (capped seed pool per lib).
    result = {}
    for lib_name, seeds in seeds_by_lib.items():
        scores = {}
        for kind, title in seeds[:10]:
            tmdb_id = _search(kind, title)
            if not tmdb_id:
                continue
            for rec in _recs(kind, tmdb_id):
                rid = rec.get("id")
                if not rid:
                    continue
                if rid in owned_tmdb.get(kind, set()):
                    continue
                k = (kind, rid)
                entry = scores.setdefault(k, {"score": 0, "data": rec, "kind": kind})
                entry["score"] += 1
        ranked = sorted(scores.values(), key=lambda x: -x["score"])
        if ranked:
            result[lib_name] = [_normalize(e["kind"], e["data"], e["score"])
                               for e in ranked[:limit_per_lib]]
    return result


# ── Music (Last.fm) ──────────────────────────────────────────────────────────

def _deezer_artist_image(artist):
    """Look up an artist's image via Deezer's free search API. Cached."""
    key = f"deezer:artist:{artist.lower()}"
    cached = _cache_get(key, SEARCH_TTL_SECS)
    if cached is not None:
        return cached or None
    try:
        r = http.get(f"{DEEZER_BASE}/search/artist",
                     params={"q": artist, "limit": 1}, timeout=10)
        r.raise_for_status()
        results = (r.json() or {}).get("data") or []
        image = results[0].get("picture_medium") if results else None
    except Exception as e:
        log.warning("deezer error for %s: %s", artist, e)
        image = None
    _cache_set(key, image)
    return image


def _lastfm_similar_artists(artist):
    """Last.fm artist.getSimilar, returns list of {name, match} dicts."""
    key = f"lastfm:similar:artist:{artist.lower()}"
    cached = _cache_get(key, RECS_TTL_SECS)
    if cached is not None:
        return cached
    if not LASTFM_API_KEY:
        return []
    try:
        r = http.get(LASTFM_BASE, params={
            "method": "artist.getSimilar",
            "artist": artist,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": 15,
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = (data.get("similarartists") or {}).get("artist") or []
    except Exception as e:
        log.warning("lastfm error for %s: %s", artist, e)
        results = []
    _cache_set(key, results)
    return results


def _seed_artists(user, limit=10):
    """Top distinct artists for the user from recent Navidrome plays."""
    with db.get_db() as conn:
        rows = conn.execute(
            """
            SELECT json_extract(item_metadata, '$.artist') AS artist,
                   COUNT(*) AS plays
            FROM events
            WHERE user_id = ? AND source = 'navidrome'
              AND played_at > date('now', '-180 days')
              AND artist IS NOT NULL AND artist != ''
            GROUP BY artist
            ORDER BY plays DESC
            LIMIT ?
            """,
            (user, limit),
        ).fetchall()
    return [r["artist"] for r in rows]


def music_recommendations(user, limit=20):
    """Return ranked artist recommendations from Last.fm based on the user's
    top recently-played Navidrome artists."""
    seeds = _seed_artists(user)
    if not seeds:
        return []

    seed_norm = {_norm(s) for s in seeds}
    owned = _navidrome_existing_artists()
    scores = {}  # norm_name -> {"score": float, "name": str, "url": str}
    for artist in seeds:
        for rec in _lastfm_similar_artists(artist):
            name = (rec.get("name") or "").strip()
            if not name:
                continue
            n = _norm(name)
            if not n or n in seed_norm or n in owned:
                continue
            try:
                match = float(rec.get("match") or 0.0)
            except Exception:
                match = 0.0
            entry = scores.setdefault(n, {
                "score": 0.0,
                "name": name,
                "url": rec.get("url", ""),
            })
            entry["score"] += match

    ranked = sorted(scores.values(), key=lambda x: -x["score"])
    return [{
        "kind": "music",
        "title": e["name"],
        "image_url": _deezer_artist_image(e["name"]),
        "request_type": "Music",
        "score": round(e["score"], 2),
        "url": e["url"],
    } for e in ranked[:limit]]


def _lastfm_similar_tracks(artist, track):
    key = f"lastfm:similar:track:{artist.lower()}::{track.lower()}"
    cached = _cache_get(key, RECS_TTL_SECS)
    if cached is not None:
        return cached
    if not LASTFM_API_KEY:
        return []
    try:
        r = http.get(LASTFM_BASE, params={
            "method": "track.getSimilar",
            "artist": artist,
            "track": track,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": 10,
        }, timeout=10)
        r.raise_for_status()
        results = ((r.json() or {}).get("similartracks") or {}).get("track") or []
    except Exception as e:
        log.warning("lastfm track error for %s - %s: %s", artist, track, e)
        results = []
    _cache_set(key, results)
    return results


def _pick_genre(tags, artist):
    """First 'real' tag, skipping the artist name itself (often the top tag
    for famous artists is just their name e.g. 'radiohead')."""
    a_norm = _norm(artist)
    for tag in tags or []:
        name = (tag.get("name") or "").strip()
        if name and _norm(name) != a_norm:
            return name
    return ""


def _lastfm_artist_top_tag(artist):
    """artist.getTopTags - genre fallback when a track has no tags. Cached 30d."""
    key = f"lastfm:artisttoptag:{artist.lower()}"
    cached = _cache_get(key, SEARCH_TTL_SECS)
    if cached is not None:
        return cached or ""
    if not LASTFM_API_KEY:
        return ""
    try:
        r = http.get(LASTFM_BASE, params={
            "method": "artist.getTopTags",
            "artist": artist,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "autocorrect": "1",
        }, timeout=10)
        r.raise_for_status()
        tags = (((r.json() or {}).get("toptags") or {}).get("tag") or [])
        genre = _pick_genre(tags, artist)
    except Exception as e:
        log.warning("lastfm artist.getTopTags error for %s: %s", artist, e)
        genre = ""
    _cache_set(key, genre)
    return genre


def _lastfm_track_info(artist, track):
    """track.getInfo + artist tag fallback. Returns {album, genre}. Cached 30d."""
    key = f"lastfm:trackinfo:v2:{artist.lower()}::{track.lower()}"
    cached = _cache_get(key, SEARCH_TTL_SECS)
    if cached is not None:
        return cached
    if not LASTFM_API_KEY:
        return {"album": "", "genre": ""}
    try:
        r = http.get(LASTFM_BASE, params={
            "method": "track.getInfo",
            "artist": artist,
            "track": track,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "autocorrect": "1",
        }, timeout=10)
        r.raise_for_status()
        t = ((r.json() or {}).get("track") or {})
        album = ((t.get("album") or {}).get("title") or "").strip()
        track_tags = ((t.get("toptags") or {}).get("tag") or [])
        genre = _pick_genre(track_tags, artist)
        if not genre:
            genre = _lastfm_artist_top_tag(artist)
        result = {"album": album, "genre": genre}
    except Exception as e:
        log.warning("lastfm track.getInfo error for %s - %s: %s", artist, track, e)
        result = {"album": "", "genre": ""}
    _cache_set(key, result)
    return result


def _seed_tracks(user, limit=10):
    with db.get_db() as conn:
        rows = conn.execute(
            """
            SELECT item_name AS title,
                   json_extract(item_metadata, '$.artist') AS artist,
                   COUNT(*) AS plays
            FROM events
            WHERE user_id = ? AND source = 'navidrome'
              AND played_at > date('now', '-180 days')
              AND artist IS NOT NULL AND artist != ''
              AND item_name IS NOT NULL AND item_name != ''
            GROUP BY artist, title
            ORDER BY plays DESC
            LIMIT ?
            """,
            (user, limit),
        ).fetchall()
    return [(r["artist"], r["title"]) for r in rows]


def song_recommendations(user, limit=25):
    seeds = _seed_tracks(user)
    if not seeds:
        return []

    seed_sig = {(_norm(a), _norm(t)) for a, t in seeds}
    owned = _navidrome_existing_tracks()
    scores = {}
    for artist, track in seeds:
        for rec in _lastfm_similar_tracks(artist, track):
            rname = (rec.get("name") or "").strip()
            rartist = ((rec.get("artist") or {}).get("name") or "").strip()
            if not rname or not rartist:
                continue
            na, nt = _norm(rartist), _norm(rname)
            if not na or not nt:
                continue
            sig = (na, nt)
            if sig in seed_sig or sig in owned:
                continue
            try:
                match = float(rec.get("match") or 0.0)
            except Exception:
                match = 0.0
            entry = scores.setdefault(sig, {
                "score": 0.0,
                "title": rname,
                "artist": rartist,
                "url": rec.get("url", ""),
            })
            entry["score"] += match

    ranked = sorted(scores.values(), key=lambda x: -x["score"])[:limit]
    out = []
    for e in ranked:
        info = _lastfm_track_info(e["artist"], e["title"])
        out.append({
            "kind": "song",
            "title":  e["title"],
            "artist": e["artist"],
            "album":  info.get("album", ""),
            "genre":  info.get("genre", ""),
            "url":    e["url"],
            "request_type": "Music",
            "score":  round(e["score"], 2),
        })
    return out
