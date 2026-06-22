"""Movie recommendations via TMDB, seeded from the user's recent Jellyfin
movie events in the stats DB."""

import logging
import os

import requests as http

import db

log = logging.getLogger("stats.recommend")

TMDB_TOKEN = os.environ.get("TMDB_TOKEN", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w342"


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


def _resolve_tmdb_id(title):
    data = _tmdb_get("/search/movie", {"query": title})
    if not data or not data.get("results"):
        return None
    return data["results"][0]["id"]


def _movie_recs(tmdb_id, limit=8):
    data = _tmdb_get(f"/movie/{tmdb_id}/recommendations")
    if not data:
        return []
    return data.get("results", [])[:limit]


def _seed_movies(user, limit=10):
    """Most-played distinct movies for the user in the last 90 days."""
    with db.get_db() as conn:
        rows = conn.execute(
            """
            SELECT item_name, COUNT(*) AS plays
            FROM events
            WHERE user_id = ?
              AND source = 'jellyfin'
              AND item_type = 'Movie'
              AND played_at > date('now', '-90 days')
            GROUP BY item_id
            ORDER BY plays DESC, MAX(played_at) DESC
            LIMIT ?
            """,
            (user, limit),
        ).fetchall()
    return [r["item_name"] for r in rows if r["item_name"]]


def movie_recommendations(user, limit=20):
    """Return up to `limit` ranked TMDB movie recommendations for the user."""
    seeds = _seed_movies(user)
    if not seeds:
        return []

    scores = {}  # tmdb_id -> {"score": int, "data": {...}}
    for title in seeds:
        tmdb_id = _resolve_tmdb_id(title)
        if not tmdb_id:
            continue
        for rec in _movie_recs(tmdb_id):
            rid = rec.get("id")
            if not rid:
                continue
            entry = scores.setdefault(rid, {"score": 0, "data": rec})
            entry["score"] += 1

    ranked = sorted(scores.values(), key=lambda x: -x["score"])
    out = []
    for entry in ranked[:limit]:
        m = entry["data"]
        out.append({
            "tmdb_id": m.get("id"),
            "title": m.get("title", ""),
            "year": (m.get("release_date") or "")[:4],
            "overview": (m.get("overview") or "")[:240],
            "poster_url": f"{TMDB_IMG_BASE}{m['poster_path']}" if m.get("poster_path") else None,
            "score": entry["score"],
        })
    return out
