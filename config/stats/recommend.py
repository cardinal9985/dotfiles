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
_ROM_EXT_RE   = re.compile(
    r"\.(?:zip|7z|rar|gz|tar|nes|smc|sfc|gba|gb|gbc|n64|z64|v64|md|smd|gen|iso|cue|bin|chd|nds|3ds|cia|psp|cso|wbfs|wad|gcm|gcz|d64|t64|a26|a52|a78|lnx|ngp|ngc|pce|sgg|sms|adf|atr|xex|rom)$",
    re.IGNORECASE,
)


# Map ROMM platform names to short tab labels.
PLATFORM_SHORT_NAMES = {
    "Arcade":                              "ARCADE",
    "Atari 2600":                          "2600",
    "Atari 5200":                          "5200",
    "Atari 7800":                          "7800",
    "Atari Lynx":                          "LYNX",
    "Atari Jaguar":                        "JAGUAR",
    "Browser (Flash/HTML5)":               "BROWSER",
    "ColecoVision":                        "COLECO",
    "Commodore 64":                        "C64",
    "Sega Game Gear":                      "GAME GEAR",
    "Sega Master System":                  "MASTER SYSTEM",
    "Sega Mega Drive/Genesis":             "GENESIS",
    "Sega Saturn":                         "SATURN",
    "Sega 32X":                            "32X",
    "Sega CD":                             "SEGA CD",
    "Sega Dreamcast":                      "DREAMCAST",
    "Nintendo 64":                         "N64",
    "Nintendo Entertainment System":       "NES",
    "Super Nintendo Entertainment System": "SNES",
    "Nintendo GameCube":                   "GAMECUBE",
    "Nintendo Wii":                        "WII",
    "Nintendo Wii U":                      "WII U",
    "Nintendo Switch":                     "SWITCH",
    "Game Boy":                            "GAME BOY",
    "Game Boy Color":                      "GBC",
    "Game Boy Advance":                    "GBA",
    "Nintendo DS":                         "DS",
    "Nintendo 3DS":                        "3DS",
    "Virtual Boy":                         "VBOY",
    "PlayStation":                         "PSX",
    "PlayStation 2":                       "PS2",
    "PlayStation 3":                       "PS3",
    "PlayStation Portable":                "PSP",
    "PlayStation Vita":                    "PS VITA",
    "Xbox":                                "XBOX",
    "Xbox 360":                            "X360",
    "TurboGrafx-16/PC Engine":             "TG16",
    "PC Engine CD/TurboGrafx-CD":          "TG-CD",
    "Neo Geo":                             "NEO GEO",
    "Neo Geo Pocket":                      "NGP",
    "Neo Geo Pocket Color":                "NGPC",
    "WonderSwan":                          "WSWAN",
    "WonderSwan Color":                    "WSWANC",
    "Magnavox Odyssey 2":                  "ODYSSEY 2",
    "Intellivision":                       "INTV",
}


def short_platform_name(name):
    return PLATFORM_SHORT_NAMES.get(name, (name or "").upper())
_ARTIST_SPLIT_RE = re.compile(r"\s*(?:,|&|/|;| x | vs\.? | feat\.? | ft\.? | featuring | with )\s*", re.IGNORECASE)


def _split_artists(s):
    """Split a multi-artist string into individual artist names.
    Handles 'A, B & C', 'A feat. B', 'A x B', 'A / B', 'A vs B', etc."""
    if not s:
        return []
    return [p for p in _ARTIST_SPLIT_RE.split(s) if p.strip()]


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

TWITCH_CLIENT_ID     = os.environ.get("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET", "")
IGDB_BASE            = "https://api.igdb.com/v4"
IGDB_IMG_BASE        = "https://images.igdb.com/igdb/image/upload/t_cover_big"
# IGDB platform IDs to exclude from recommendation filtering even if the user
# has ROMs configured for them. Browser (Flash/HTML5) sweeps in thousands of
# modern HTML5 games and pollutes the retro feed.
IGDB_RECS_EXCLUDED_PLATFORMS = {82}

JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://127.0.0.1:8096")
JELLYFIN_API_KEY = os.environ.get("JELLYFIN_API_KEY", "")
NAVIDROME_DB = os.environ.get("NAVIDROME_DB", "/var/lib/navidrome/navidrome.db")

ROMM_DB_HOST     = os.environ.get("ROMM_DB_HOST", "127.0.0.1")
ROMM_DB_PORT     = int(os.environ.get("ROMM_DB_PORT", "3308"))
ROMM_DB_NAME     = os.environ.get("ROMM_DB_NAME", "romm")
ROMM_DB_USER     = os.environ.get("ROMM_DB_USER", "romm")
ROMM_DB_PASSWORD = os.environ.get("ROMM_DB_PASSWORD", "")

BOOKLORE_DB_HOST     = os.environ.get("BOOKLORE_DB_HOST", "127.0.0.1")
BOOKLORE_DB_PORT     = int(os.environ.get("BOOKLORE_DB_PORT", "3306"))
BOOKLORE_DB_NAME     = os.environ.get("BOOKLORE_DB_NAME", "booklore")
BOOKLORE_DB_USER     = os.environ.get("BOOKLORE_DB_USER", "booklore")
BOOKLORE_DB_PASSWORD = os.environ.get("BOOKLORE_DB_PASSWORD", "")

OPENLIBRARY_BASE = "https://openlibrary.org"
OPENLIBRARY_COVERS = "https://covers.openlibrary.org"

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


# ── Books (OpenLibrary) ──────────────────────────────────────────────────────

def _openlibrary_get(path, params=None):
    try:
        r = http.get(f"{OPENLIBRARY_BASE}{path}", params=params, timeout=15,
                     headers={"User-Agent": "ishimura-stats/1.0"})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("openlibrary %s %s: %s", path, params, e)
        return None


def _openlibrary_books_by_author(author):
    """List of book dicts by an author. Cached 30d."""
    key = f"openlibrary:author:{author.lower()}"
    cached = _cache_get(key, SEARCH_TTL_SECS)
    if cached is not None:
        return cached
    data = _openlibrary_get("/search.json", {
        "author": author,
        "limit":  20,
        "sort":   "rating",
    })
    books = []
    for d in (data or {}).get("docs", []) or []:
        books.append({
            "title":         d.get("title") or "",
            "year":          d.get("first_publish_year"),
            "author_names":  (d.get("author_name") or [])[:2],
            "cover_id":      d.get("cover_i"),
            "subjects":      (d.get("subject") or [])[:3],
            "edition_count": d.get("edition_count") or 0,
        })
    _cache_set(key, books)
    return books


def _booklore_existing_books():
    """Normalized set of book titles already in the user's BookLore library."""
    key = "booklore:existing_books:v1"
    cached = _cache_get(key, LIBRARY_TTL_SECS)
    if cached is not None:
        return set(cached)
    if not BOOKLORE_DB_PASSWORD:
        return set()
    try:
        import pymysql
        bl = pymysql.connect(
            host=BOOKLORE_DB_HOST, port=BOOKLORE_DB_PORT,
            user=BOOKLORE_DB_USER, password=BOOKLORE_DB_PASSWORD,
            database=BOOKLORE_DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )
        try:
            with bl.cursor() as cur:
                cur.execute("""
                    SELECT bm.title FROM book b
                    JOIN book_metadata bm ON b.id = bm.book_id
                    WHERE b.deleted = 0 AND bm.title IS NOT NULL
                """)
                rows = cur.fetchall()
        finally:
            bl.close()
        titles = sorted({_norm(r["title"]) for r in rows if r.get("title")})
        titles = [t for t in titles if t]
    except Exception as e:
        log.warning("booklore book scan failed: %s", e)
        titles = []
    _cache_set(key, titles)
    return set(titles)


def _seed_books(user, limit=10):
    """Most-recent distinct books the user has read in the last year, with
    author parsed out of the event metadata."""
    with db.get_db() as conn:
        rows = conn.execute(
            """
            SELECT item_name AS title,
                   json_extract(item_metadata, '$.author') AS author,
                   MAX(played_at) AS recent
            FROM events
            WHERE user_id = ? AND source = 'booklore'
              AND played_at > date('now', '-365 days')
              AND item_name IS NOT NULL AND item_name != ''
            GROUP BY item_id
            ORDER BY recent DESC
            LIMIT ?
            """,
            (user, limit),
        ).fetchall()
    seeds = []
    seen_authors = set()
    for r in rows:
        # Each author string may list multiple authors; split & use each.
        for a in _split_artists(r["author"] or ""):
            an = _norm(a)
            if an and an not in seen_authors:
                seen_authors.add(an)
                seeds.append(a.strip())
    return seeds


def book_recommendations(user, limit=20):
    """Recommend books by authors you've read, filtered against your library."""
    seed_authors = _seed_books(user)
    if not seed_authors:
        return []

    owned = _booklore_existing_books()
    seed_titles_norm = set()
    # Also collect titles already in the library so we don't re-suggest books
    # we own even if the user happened to read one (we want NEW books).
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT item_name FROM events "
            "WHERE user_id=? AND source='booklore'",
            (user,),
        ).fetchall()
    for r in rows:
        if r["item_name"]:
            seed_titles_norm.add(_norm(r["item_name"]))

    scores = {}  # norm_title -> {"score": int, "book": dict}
    for author in seed_authors:
        for b in _openlibrary_books_by_author(author):
            title = b.get("title") or ""
            n = _norm(title)
            if not n or n in seed_titles_norm or n in owned:
                continue
            entry = scores.setdefault(n, {"score": 0, "book": b})
            entry["score"] += max(1, (b.get("edition_count") or 1))

    ranked = sorted(scores.values(), key=lambda x: -x["score"])
    out = []
    for e in ranked[:limit]:
        b = e["book"]
        cover = (f"{OPENLIBRARY_COVERS}/b/id/{b['cover_id']}-M.jpg"
                 if b.get("cover_id") else None)
        out.append({
            "kind":         "book",
            "title":        b.get("title", ""),
            "year":         str(b.get("year") or ""),
            "author":       ", ".join(b.get("author_names") or []),
            "overview":     "",
            "cover_url":    cover,
            "request_type": "Book",
            "score":        e["score"],
        })
    return out


def library_check(req_type, title):
    """Used by the requests app to know whether a requested item is already
    available somewhere in our libraries. Returns {'exists': bool,
    'match': str|None} where match is a human-readable description of what
    we found."""
    n = _norm(title)
    if not n:
        return {"exists": False, "match": None}

    rt = (req_type or "").lower()

    if rt in ("movie", "show"):
        libs = _jellyfin_libraries()
        kind_filter = "Movie" if rt == "movie" else "Series"
        for lib in libs:
            for it in _jellyfin_library_items(lib["id"]):
                if it.get("type") != kind_filter:
                    continue
                if _norm(it.get("name") or "") == n:
                    return {
                        "exists": True,
                        "match":  f"{it['name']} ({lib['name']})",
                    }
        return {"exists": False, "match": None}

    if rt == "music":
        artists = _navidrome_existing_artists()
        if n in artists:
            return {"exists": True, "match": f"{title} (Navidrome)"}
        return {"exists": False, "match": None}

    if rt == "book":
        owned = _booklore_existing_books()
        if n in owned:
            return {"exists": True, "match": f"{title} (BookLore)"}
        return {"exists": False, "match": None}

    if rt == "game":
        owned = _romm_existing_games()
        if n in owned:
            return {"exists": True, "match": f"{title} (ROMM)"}
        return {"exists": False, "match": None}

    return {"exists": False, "match": None}


def warm_cache_for(user):
    """Run all recommendation builds. Slow first time, fast after (cached)."""
    video_recommendations_by_library(user)
    music_recommendations(user)
    song_recommendations(user)
    game_recommendations_by_platform(user)
    book_recommendations(user)


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
    """Set of normalized artist + album_artist names in the user's library.
    Multi-artist strings are split so each individual artist matches."""
    key = "navidrome:existing_artists:v5"
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
        names = set()
        for r in rows:
            if not r[0]:
                continue
            for part in _split_artists(r[0]):
                n = _norm(part)
                if n:
                    names.add(n)
        names_list = sorted(names)
    except Exception as e:
        log.warning("navidrome artist scan failed: %s", e)
        names_list = []
    _cache_set(key, names_list)
    return set(names_list)


def _navidrome_existing_tracks():
    """Set of (normalized_artist, normalized_title) tuples in the library.
    Splits multi-artist strings ('A & B', 'A feat. B', etc.) so a Last.fm
    rec naming just one of the collaborators still matches."""
    key = "navidrome:existing_tracks:v5"
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
            for field in (artist, album_artist):
                if not field:
                    continue
                for part in _split_artists(field):
                    a = _norm(part)
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
            if not n:
                continue
            # Skip if the rec OR any of its split parts overlaps with what
            # we've seeded or already have in the library.
            parts = [_norm(p) for p in _split_artists(name)]
            parts = [p for p in parts if p]
            check_set = set(parts) | {n}
            if check_set & seed_norm or check_set & owned:
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


# ── Games (IGDB via Twitch OAuth) ────────────────────────────────────────────

def _igdb_token():
    """Fetch and cache an IGDB access token via Twitch client_credentials.
    Twitch tokens last ~60 days; we cache for 30 to leave headroom."""
    key = "igdb:token"
    cached = _cache_get(key, 30 * 86400)
    if cached:
        return cached
    if not (TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET):
        return ""
    try:
        r = http.post("https://id.twitch.tv/oauth2/token", params={
            "client_id":     TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type":    "client_credentials",
        }, timeout=10)
        r.raise_for_status()
        token = (r.json() or {}).get("access_token", "")
    except Exception as e:
        log.warning("igdb token error: %s", e)
        return ""
    if token:
        _cache_set(key, token)
    return token


def _igdb_post(endpoint, body):
    """POST an Apicalypse query body to IGDB. Returns parsed JSON or []."""
    token = _igdb_token()
    if not token or not TWITCH_CLIENT_ID:
        return []
    try:
        r = http.post(
            f"{IGDB_BASE}/{endpoint}",
            headers={
                "Client-ID":     TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {token}",
                "Accept":        "application/json",
            },
            data=body,
            timeout=15,
        )
        r.raise_for_status()
        return r.json() or []
    except Exception as e:
        log.warning("igdb %s error: %s", endpoint, e)
        return []


def _igdb_search(name):
    """Find an IGDB game ID by name. Returns int or None."""
    key = f"igdb:search:{name.lower()}"
    cached = _cache_get(key, SEARCH_TTL_SECS)
    if cached is not None:
        return cached or None
    # Escape double quotes in the name.
    safe = name.replace('"', '\\"')
    results = _igdb_post("games", f'search "{safe}"; fields id; limit 1;')
    game_id = results[0]["id"] if results else None
    _cache_set(key, game_id)
    return game_id


def _igdb_similar(game_id, limit=10):
    """Get similar games for a game. Returns normalized list of dicts including
    the list of IGDB platform IDs each game is available on."""
    key = f"igdb:similar:v2:{game_id}"
    cached = _cache_get(key, RECS_TTL_SECS)
    if cached is not None:
        return cached[:limit]
    body = (
        "fields similar_games.id, similar_games.name, "
        "similar_games.cover.image_id, similar_games.first_release_date, "
        "similar_games.summary, similar_games.platforms; "
        f"where id = {game_id};"
    )
    results = _igdb_post("games", body)
    similar = []
    if results:
        for g in (results[0].get("similar_games") or []):
            cover = (g.get("cover") or {}).get("image_id")
            year = ""
            if g.get("first_release_date"):
                try:
                    year = str(datetime.fromtimestamp(g["first_release_date"]).year)
                except Exception:
                    year = ""
            similar.append({
                "id":        g.get("id"),
                "name":      g.get("name", ""),
                "year":      year,
                "summary":   (g.get("summary") or "")[:240],
                "cover_url": f"{IGDB_IMG_BASE}/{cover}.jpg" if cover else None,
                "platforms": g.get("platforms") or [],
            })
    _cache_set(key, similar)
    return similar[:limit]


def _romm_owned_platforms():
    """Set of IGDB platform IDs the user has ROMs for. Used to filter game
    recommendations to platforms ROMM can actually serve."""
    key = "romm:owned_platforms:v1"
    cached = _cache_get(key, LIBRARY_TTL_SECS)
    if cached is not None:
        return set(cached)
    if not ROMM_DB_PASSWORD:
        return set()
    try:
        import pymysql
        rm = pymysql.connect(
            host=ROMM_DB_HOST, port=ROMM_DB_PORT,
            user=ROMM_DB_USER, password=ROMM_DB_PASSWORD,
            database=ROMM_DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )
        try:
            with rm.cursor() as cur:
                cur.execute("SELECT DISTINCT igdb_id FROM platforms WHERE igdb_id IS NOT NULL")
                ids = [int(r["igdb_id"]) for r in cur.fetchall() if r.get("igdb_id")]
        finally:
            rm.close()
    except Exception as e:
        log.warning("romm platform scan failed: %s", e)
        ids = []
    _cache_set(key, ids)
    return set(ids)


def _romm_existing_games():
    """Normalized set of game names already in the user's ROMM library."""
    key = "romm:existing_games:v1"
    cached = _cache_get(key, LIBRARY_TTL_SECS)
    if cached is not None:
        return set(cached)
    if not ROMM_DB_PASSWORD:
        return set()
    try:
        import pymysql
        rm = pymysql.connect(
            host=ROMM_DB_HOST, port=ROMM_DB_PORT,
            user=ROMM_DB_USER, password=ROMM_DB_PASSWORD,
            database=ROMM_DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )
        try:
            with rm.cursor() as cur:
                cur.execute("SELECT name, fs_name FROM roms")
                rows = cur.fetchall()
        finally:
            rm.close()
        names = set()
        for r in rows:
            for field in (r.get("name"), r.get("fs_name")):
                if field:
                    n = _norm(field)
                    if n:
                        names.add(n)
        names_list = sorted(names)
    except Exception as e:
        log.warning("romm game scan failed: %s", e)
        names_list = []
    _cache_set(key, names_list)
    return set(names_list)


def _seed_games_by_platform(user, limit_per=10):
    """Recent ROMM seeds grouped by the platform_name stored in the event
    metadata. Returns dict {platform_name: [cleaned_game_names]}."""
    with db.get_db() as conn:
        rows = conn.execute(
            """
            SELECT item_name,
                   json_extract(item_metadata, '$.platform') AS platform,
                   item_id,
                   COUNT(*) AS plays,
                   MAX(played_at) AS recent
            FROM events
            WHERE user_id = ? AND source = 'romm'
              AND played_at > date('now', '-180 days')
              AND item_name IS NOT NULL AND item_name != ''
              AND platform  IS NOT NULL AND platform  != ''
            GROUP BY platform, item_id
            ORDER BY plays DESC, recent DESC
            """,
            (user,),
        ).fetchall()
    by_platform = {}
    for r in rows:
        name = r["item_name"]
        # Strip ROM file extension (.zip / .a26 / .nes / etc.) then regional
        # tags like (USA), (Disc 1) so IGDB search has a clean title.
        name = _ROM_EXT_RE.sub("", name)
        cleaned = _PARENS_RE.sub("", name).strip()
        if cleaned:
            by_platform.setdefault(r["platform"], []).append(cleaned)
    # Cap seeds per platform.
    return {p: games[:limit_per] for p, games in by_platform.items()}


def _romm_platform_map():
    """ROMM platform name -> IGDB platform id."""
    key = "romm:platform_map:v1"
    cached = _cache_get(key, LIBRARY_TTL_SECS)
    if cached is not None:
        return cached
    if not ROMM_DB_PASSWORD:
        return {}
    try:
        import pymysql
        rm = pymysql.connect(
            host=ROMM_DB_HOST, port=ROMM_DB_PORT,
            user=ROMM_DB_USER, password=ROMM_DB_PASSWORD,
            database=ROMM_DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )
        try:
            with rm.cursor() as cur:
                cur.execute(
                    "SELECT name, custom_name, igdb_id FROM platforms "
                    "WHERE igdb_id IS NOT NULL"
                )
                rows = cur.fetchall()
        finally:
            rm.close()
        mapping = {}
        for r in rows:
            for n in (r.get("name"), r.get("custom_name")):
                if n:
                    mapping[n] = int(r["igdb_id"])
    except Exception as e:
        log.warning("romm platform map failed: %s", e)
        mapping = {}
    _cache_set(key, mapping)
    return mapping


def _igdb_game_genres(game_id):
    """Genre IDs for a single IGDB game. Cached 30d."""
    key = f"igdb:genres:{game_id}"
    cached = _cache_get(key, SEARCH_TTL_SECS)
    if cached is not None:
        return cached
    results = _igdb_post("games", f"fields genres; where id = {game_id};")
    genres = (results[0].get("genres") if results else []) or []
    _cache_set(key, genres)
    return genres


def _igdb_top_in_genres_on_platforms(genre_ids, platform_ids, limit=60):
    """Highly-rated games matching any of the genres on any of the platforms."""
    if not genre_ids or not platform_ids:
        return []
    g_key = ",".join(str(g) for g in sorted(genre_ids))
    p_key = ",".join(str(p) for p in sorted(platform_ids))
    key = f"igdb:topby:v3:{g_key}|{p_key}|{limit}"
    cached = _cache_get(key, RECS_TTL_SECS)
    if cached is not None:
        return cached
    g_clause = "(" + ",".join(str(g) for g in genre_ids) + ")"
    p_clause = "(" + ",".join(str(p) for p in platform_ids) + ")"
    body = (
        "fields id, name, cover.image_id, first_release_date, summary, "
        "platforms, total_rating, total_rating_count; "
        f"where genres = {g_clause} & platforms = {p_clause} "
        "& total_rating > 70 & total_rating_count > 5; "
        f"sort total_rating desc; limit {limit};"
    )
    results = _igdb_post("games", body)
    games = []
    for g in results:
        cover = (g.get("cover") or {}).get("image_id")
        year = ""
        if g.get("first_release_date"):
            try:
                year = str(datetime.fromtimestamp(g["first_release_date"]).year)
            except Exception:
                year = ""
        games.append({
            "id":        g.get("id"),
            "name":      g.get("name", ""),
            "year":      year,
            "summary":   (g.get("summary") or "")[:240],
            "cover_url": f"{IGDB_IMG_BASE}/{cover}.jpg" if cover else None,
            "rating":    g.get("total_rating") or 0,
        })
    _cache_set(key, games)
    return games


def game_recommendations_by_platform(user, limit_per=15):
    """Recommend games grouped by platform: for each platform the user has
    seeds on, query IGDB for top-rated games in matching genres limited to
    that single platform. Dedupes against the ROMM library."""
    seeds_by_platform = _seed_games_by_platform(user)
    if not seeds_by_platform:
        return {}

    platform_map = _romm_platform_map()
    owned        = _romm_existing_games()

    result = {}
    for platform_name, seeds in seeds_by_platform.items():
        igdb_pid = platform_map.get(platform_name)
        if not igdb_pid or igdb_pid in IGDB_RECS_EXCLUDED_PLATFORMS:
            continue

        # Aggregate genres from this platform's seeds.
        seed_genres = set()
        for game in seeds:
            gid = _igdb_search(game)
            if gid:
                seed_genres.update(_igdb_game_genres(gid))
        if not seed_genres:
            continue

        candidates = _igdb_top_in_genres_on_platforms(
            sorted(seed_genres), [igdb_pid], limit=40
        )

        seed_norm = {_norm(s) for s in seeds}
        out = []
        for g in candidates:
            name = g.get("name", "")
            n = _norm(name)
            if not n or n in seed_norm or n in owned:
                continue
            out.append({
                "kind":         "game",
                "title":        name,
                "year":         g.get("year", ""),
                "overview":     g.get("summary", ""),
                "cover_url":    g.get("cover_url"),
                "request_type": "Game",
                "score":        round(g.get("rating", 0), 1),
            })
            if len(out) >= limit_per:
                break

        if out:
            result[platform_name] = out
    return result


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
            nt = _norm(rname)
            if not nt:
                continue
            # Check the rec artist string as a whole AND each split part.
            na = _norm(rartist)
            parts = [_norm(p) for p in _split_artists(rartist)]
            parts = [p for p in parts if p]
            sigs = {(p, nt) for p in parts} | {(na, nt)}
            if sigs & seed_sig or sigs & owned:
                continue
            sig = (na, nt)
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
