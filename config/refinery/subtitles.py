"""OpenSubtitles v1 REST client for auto-fetching subtitle sidecars on approve.

Flow per video:
  1. Search /subtitles with tmdb_id (or imdb_id, or by name) + languages.
  2. For each requested language, pick the top-ranked result.
  3. POST /download {file_id} -> get a temporary download URL.
  4. GET the URL, save as `<video-stem>.<lang>.srt` next to the video.

Auth: Api-Key header + Bearer token from /login. Token TTL ~24h; we
re-login on 401.

Best-effort: any failure returns without downloading. Missing API key
disables the module entirely. Env vars:
  OPENSUBTITLES_API_KEY  (required to enable)
  OPENSUBTITLES_USERNAME (optional - gives 20/day instead of 5/day)
  OPENSUBTITLES_PASSWORD (optional)
  REFINERY_SUBTITLE_LANGS (comma-separated, default 'en')
"""

import logging
import os
import time
from pathlib import Path

import requests

log = logging.getLogger("refinery.subtitles")

API_BASE = "https://api.opensubtitles.com/api/v1"
UA       = "ishimura-refinery/1.0"

DEFAULT_LANGS = [
    s.strip().lower() for s in
    os.environ.get("REFINERY_SUBTITLE_LANGS", "en").split(",")
    if s.strip()
]

_token = {"value": None, "expires_at": 0.0}


def _key():
    return os.environ.get("OPENSUBTITLES_API_KEY", "").strip()


def _login_creds():
    return (os.environ.get("OPENSUBTITLES_USERNAME", "").strip(),
            os.environ.get("OPENSUBTITLES_PASSWORD", "").strip())


def enabled():
    return bool(_key())


def _headers(with_bearer=False):
    h = {
        "Api-Key":    _key(),
        "User-Agent": UA,
        "Accept":     "application/json",
    }
    if with_bearer and _token["value"]:
        h["Authorization"] = f"Bearer {_token['value']}"
    return h


def _login():
    """Grab a Bearer token. Without a login the download quota is much
    lower (5/day vs 20/day) - we still try to work anonymous if the
    username/password aren't configured."""
    user, pw = _login_creds()
    if not user or not pw:
        return None
    if _token["value"] and _token["expires_at"] > time.time() + 60:
        return _token["value"]
    try:
        r = requests.post(f"{API_BASE}/login",
                          headers={**_headers(), "Content-Type": "application/json"},
                          json={"username": user, "password": pw},
                          timeout=15)
        r.raise_for_status()
        j = r.json()
        _token["value"]      = j.get("token")
        # Docs say the token is valid for 24h; be a bit conservative.
        _token["expires_at"] = time.time() + 20 * 3600
        return _token["value"]
    except Exception as e:
        log.warning("opensubtitles login failed: %s", e)
        return None


def _get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}",
                         headers=_headers(with_bearer=True),
                         params=params or {},
                         timeout=15)
        if r.status_code == 401 and _login_creds()[0]:
            _token["value"] = None
            _login()
            r = requests.get(f"{API_BASE}{path}",
                             headers=_headers(with_bearer=True),
                             params=params or {},
                             timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("opensubtitles GET %s failed: %s", path, e)
        return None


def _post_download(file_id):
    try:
        r = requests.post(f"{API_BASE}/download",
                          headers={**_headers(with_bearer=True),
                                   "Content-Type": "application/json"},
                          json={"file_id": file_id},
                          timeout=15)
        if r.status_code == 401 and _login_creds()[0]:
            _token["value"] = None
            _login()
            r = requests.post(f"{API_BASE}/download",
                              headers={**_headers(with_bearer=True),
                                       "Content-Type": "application/json"},
                              json={"file_id": file_id},
                              timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("opensubtitles download-req failed for %s: %s",
                    file_id, e)
        return None


def _search(languages, tmdb_id=None, imdb_id=None, parent_tmdb_id=None,
            season_no=None, episode_no=None, query=None):
    """Movies: tmdb_id or imdb_id (or query). Episodes: parent_tmdb_id +
    season_number + episode_number. `languages` is comma-separated."""
    params = {"languages": ",".join(languages)}
    if parent_tmdb_id and season_no is not None and episode_no is not None:
        params["parent_tmdb_id"]  = parent_tmdb_id
        params["season_number"]   = season_no
        params["episode_number"]  = episode_no
    elif tmdb_id:
        params["tmdb_id"] = tmdb_id
    elif imdb_id:
        params["imdb_id"] = imdb_id.lstrip("t")
    elif query:
        params["query"] = query
    else:
        return None
    return _get("/subtitles", params=params)


def _pick_best_per_language(results, languages):
    """OpenSubtitles ranks by download count within a language. Keep the
    top-scoring result per requested language."""
    picks = {}
    for item in results or []:
        attrs = item.get("attributes") or {}
        lang  = (attrs.get("language") or "").lower()
        if lang not in languages:
            continue
        if lang in picks:
            continue
        files = attrs.get("files") or []
        if not files:
            continue
        picks[lang] = {
            "file_id":       files[0].get("file_id"),
            "language":      lang,
            "release":       attrs.get("release"),
            "download_count": attrs.get("download_count"),
        }
    return picks


def _write_srt(video_path, lang, download_url):
    """Fetch download_url and save as `<stem>.<lang>.srt`. Returns dest
    path on success."""
    video = Path(video_path)
    dest  = video.with_suffix("")
    dest  = dest.with_name(f"{dest.name}.{lang}.srt")
    try:
        r = requests.get(download_url, timeout=60, stream=True,
                         headers={"User-Agent": UA})
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        log.info("subtitle saved: %s", dest)
        return str(dest)
    except Exception as e:
        log.warning("subtitle download failed %s: %s", download_url, e)
        try:
            if dest.exists():
                dest.unlink()
        except Exception:
            pass
        return None


def fetch_for_video(video_path, tmdb_id=None, imdb_id=None,
                    parent_tmdb_id=None, season_no=None, episode_no=None,
                    query=None, languages=None):
    """Top-level entry: find + download subs for one video file. Returns
    list of downloaded paths (may be empty)."""
    if not enabled():
        return []
    langs = [l.lower() for l in (languages or DEFAULT_LANGS)]
    if not langs:
        return []
    _login()  # best-effort - anonymous still gets a smaller quota

    j = _search(langs, tmdb_id=tmdb_id, imdb_id=imdb_id,
                parent_tmdb_id=parent_tmdb_id,
                season_no=season_no, episode_no=episode_no, query=query)
    if not j:
        return []
    picks = _pick_best_per_language(j.get("data") or [], langs)

    written = []
    for lang, pick in picks.items():
        fid = pick["file_id"]
        if not fid:
            continue
        dl = _post_download(fid)
        if not dl or not dl.get("link"):
            log.info("no download link (quota?) for %s [%s]",
                     video_path, lang)
            continue
        path = _write_srt(video_path, lang, dl["link"])
        if path:
            written.append(path)
    return written
