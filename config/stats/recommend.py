"""Movie recommendations via TMDB, seeded from the user's recent Jellyfin
movie events in the stats DB."""

import json
import logging
import os
from datetime import datetime

import requests as http

import db

log = logging.getLogger("stats.recommend")

TMDB_TOKEN = os.environ.get("TMDB_TOKEN", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w342"

LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "")
LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"

DEEZER_BASE = "https://api.deezer.com"

# Cache TTLs. Title->ID rarely changes, so we keep it ~30 days. Recommendations
# get refreshed weekly since TMDB tweaks their algorithm over time.
SEARCH_TTL_SECS = 30 * 86400
RECS_TTL_SECS   = 7 * 86400


def cache_is_warm():
    """Quick check: does the api_cache have any entries? Used by the route
    to decide whether to show a 'building recommendations' loading screen."""
    with db.get_db() as conn:
        row = conn.execute("SELECT 1 FROM api_cache LIMIT 1").fetchone()
    return row is not None


def warm_cache_for(user):
    """Run all recommendation builds. Slow first time, fast after (cached)."""
    movie_recommendations(user)
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


def movie_recommendations(user, limit=20):
    """Return up to `limit` ranked TMDB recommendations seeded from the
    user's recent movies and TV shows. Mixed movie + TV output."""
    seeds = _seed_titles(user)
    if not seeds:
        return []

    scores = {}  # (kind, tmdb_id) -> {"score": int, "data": ...}
    for kind, title in seeds:
        tmdb_id = _search(kind, title)
        if not tmdb_id:
            continue
        for rec in _recs(kind, tmdb_id):
            rid = rec.get("id")
            if not rid:
                continue
            key = (kind, rid)
            entry = scores.setdefault(key, {"score": 0, "data": rec, "kind": kind})
            entry["score"] += 1

    ranked = sorted(scores.values(), key=lambda x: -x["score"])
    return [_normalize(e["kind"], e["data"], e["score"]) for e in ranked[:limit]]


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

    seed_lower = {s.lower() for s in seeds}
    scores = {}  # artist_lower -> {"score": float, "name": str, "url": str}
    for artist in seeds:
        for rec in _lastfm_similar_artists(artist):
            name = (rec.get("name") or "").strip()
            if not name or name.lower() in seed_lower:
                continue
            try:
                match = float(rec.get("match") or 0.0)
            except Exception:
                match = 0.0
            entry = scores.setdefault(name.lower(), {
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

    seed_sig = {f"{a.lower()}::{t.lower()}" for a, t in seeds}
    scores = {}
    for artist, track in seeds:
        for rec in _lastfm_similar_tracks(artist, track):
            rname = (rec.get("name") or "").strip()
            rartist = ((rec.get("artist") or {}).get("name") or "").strip()
            if not rname or not rartist:
                continue
            sig = f"{rartist.lower()}::{rname.lower()}"
            if sig in seed_sig:
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

    ranked = sorted(scores.values(), key=lambda x: -x["score"])
    return [{
        "kind": "song",
        "title": e["title"],
        "artist": e["artist"],
        "url": e["url"],
        "request_type": "Music",
        "score": round(e["score"], 2),
    } for e in ranked[:limit]]
