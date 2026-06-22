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

# Cache TTLs. Title->ID rarely changes, so we keep it ~30 days. Recommendations
# get refreshed weekly since TMDB tweaks their algorithm over time.
SEARCH_TTL_SECS = 30 * 86400
RECS_TTL_SECS   = 7 * 86400


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
