"""IGDB metadata client.

IGDB sits behind Twitch OAuth: fetch a client-credentials access token from
id.twitch.tv, use it against api.igdb.com. Token lifetime is generous
(~60 days) but we still respect the returned expires_in and refresh lazily.

Cover art comes from images.igdb.com under a size template like
t_cover_big. Cached to REFINERY_GAME_COVER_DIR so re-approves and
re-processes don't hammer the CDN.

Every call is best-effort: any failure returns None so the approve flow
still works without metadata. IGDB_CLIENT_ID / IGDB_CLIENT_SECRET come
from sops via the systemd EnvironmentFile."""

import logging
import os
import time

import requests

log = logging.getLogger("refinery.igdb")

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_API         = "https://api.igdb.com/v4"
IMG_BASE         = "https://images.igdb.com/igdb/image/upload"
UA               = "ishimura-refinery/1.0 (https://refinery.ishimura.lol)"

# In-process token cache. Twitch client-credentials tokens are long-lived
# so process lifetime is well within one token's validity.
_token = {"value": None, "expires_at": 0.0}


def _client():
    cid = os.environ.get("IGDB_CLIENT_ID", "").strip()
    sec = os.environ.get("IGDB_CLIENT_SECRET", "").strip()
    return (cid, sec) if cid and sec else (None, None)


def enabled():
    cid, sec = _client()
    return bool(cid and sec)


def _get_token():
    cid, sec = _client()
    if not cid:
        return None
    if _token["value"] and _token["expires_at"] > time.time() + 60:
        return _token["value"]
    try:
        r = requests.post(TWITCH_TOKEN_URL, params={
            "client_id":     cid,
            "client_secret": sec,
            "grant_type":    "client_credentials",
        }, timeout=15)
        r.raise_for_status()
        j = r.json()
        _token["value"]      = j["access_token"]
        _token["expires_at"] = time.time() + int(j.get("expires_in", 3600))
        return _token["value"]
    except Exception as e:
        log.warning("twitch token fetch failed: %s", e)
        return None


def _api(endpoint, body):
    cid, _ = _client()
    tok = _get_token()
    if not (cid and tok):
        return None
    try:
        r = requests.post(f"{IGDB_API}/{endpoint}", data=body,
                          headers={
                              "Client-ID":     cid,
                              "Authorization": f"Bearer {tok}",
                              "User-Agent":    UA,
                              "Content-Type":  "text/plain",
                          }, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("IGDB %s failed: %s", endpoint, e)
        return None


def _escape(s):
    # IGDB Apicalypse uses double-quoted strings; downgrade any embedded
    # double-quote so the search literal stays valid.
    return (s or "").replace('"', "'").replace("\\", "")


def search_game(title, igdb_platform_id=None):
    """Look up a game by title, optionally scoped to a platform. Returns a
    small dict or None. `search` and `where` combine in Apicalypse, giving
    us ranked matches restricted to the right console."""
    if not title:
        return None
    fields = ("fields name,cover.image_id,first_release_date,"
              "genres.name,summary,platforms,"
              "involved_companies.company.name,"
              "involved_companies.developer,"
              "involved_companies.publisher;")
    where = (f"where platforms = ({int(igdb_platform_id)});"
             if igdb_platform_id else "")
    body = f'search "{_escape(title)}"; {fields} {where} limit 1;'
    j = _api("games", body)
    if not j:
        return None
    g = j[0]

    year = None
    if g.get("first_release_date"):
        try:
            year = time.gmtime(int(g["first_release_date"])).tm_year
        except Exception:
            pass

    developer = None
    publisher = None
    for ic in g.get("involved_companies") or []:
        name = (ic.get("company") or {}).get("name")
        if not name:
            continue
        if ic.get("developer") and not developer:
            developer = name
        if ic.get("publisher") and not publisher:
            publisher = name

    genres    = [x["name"] for x in g.get("genres") or [] if x.get("name")]
    cover_id  = (g.get("cover") or {}).get("image_id")
    summary   = (g.get("summary") or "").strip()

    return {
        "igdb_id":   g.get("id"),
        "name":      g.get("name"),
        "year":      year,
        "developer": developer,
        "publisher": publisher,
        "genres":    genres,
        "genre":     genres[0] if genres else None,
        "summary":   summary[:1200],
        "cover_id":  cover_id,
    }


def download_cover(cover_id, dest_dir, size="t_cover_big"):
    """Fetch cover art. Idempotent: skips the network if we already have
    the file on disk. Returns local path or None."""
    if not cover_id:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"{cover_id}.jpg")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    try:
        r = requests.get(f"{IMG_BASE}/{size}/{cover_id}.jpg",
                         headers={"User-Agent": UA},
                         timeout=30, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return dest
    except Exception as e:
        log.warning("igdb cover download failed for %s: %s", cover_id, e)
        return None
