"""Video processor: films and TV shows / anime / documentaries.

Pipeline per download entry:
  1. Walk the folder for video files; parse each with guessit (title, year,
     season, episode).
  2. Group episodes by (show title, season) -> one item per season with the
     episode files as tracks. Movies stay one file = one item.
  3. Look up each item on TMDB (movie or tv) for canonical title / year /
     poster / overview / genre. Derive the subtype:
       - anime_*: origin JP + Animation genre
       - documentary / docuseries: Documentary genre
       - short_film: movie with TMDB runtime < 40 min
       - movie / show: otherwise
  4. Stage in the queue at 'ready'. On approve, move to
     <target-for-subtype>/... in the Jellyfin-recommended layout.

Metadata source: TMDB v4 read-token (Authorization: Bearer). Set TMDB_TOKEN
via sops. Filename parse: guessit."""

import json
import logging
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path

import requests as http

import db
import subtitles
import targets

try:
    from guessit import guessit
except ImportError:
    guessit = None

log = logging.getLogger("refinery.video")

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v"}
SIDECAR_EXTS = {".srt", ".ass", ".ssa", ".sub", ".idx", ".vtt", ".nfo", ".jpg",
                ".jpeg", ".png"}
SUBTITLE_EXTS = {".srt", ".ass", ".ssa", ".sub", ".idx", ".vtt"}

# Torrent samples: usually named `sample.<ext>` or `<title>-sample.<ext>`, and
# always tiny (< 100 MB even for a 4K sample). Skip so we don't stage the
# preview clip as a movie item alongside the real one.
SAMPLE_MAX_BYTES = 100 * 1024 * 1024
SAMPLE_RE = re.compile(r"(?:^|[\s._-])sample(?:[\s._-]|$)", re.IGNORECASE)

VIDEO_COVER_DIR = os.environ.get("REFINERY_VIDEO_COVER_DIR",
                                 "/persist/refinery/video_covers")

TMDB_TOKEN = os.environ.get("TMDB_TOKEN", "").strip()
TMDB_BASE  = "https://api.themoviedb.org/3"
TMDB_IMG   = "https://image.tmdb.org/t/p/w780"

SHORT_FILM_MAX_MINUTES = 40

# TMDB fixed genre ids we care about for classification. Full list at
# /genre/movie/list, /genre/tv/list. These two IDs are stable.
TMDB_GENRE_ANIMATION   = 16
TMDB_GENRE_DOCUMENTARY = 99


def tmdb_enabled():
    return bool(TMDB_TOKEN)


def _tmdb_get(path, params=None):
    if not TMDB_TOKEN:
        return None
    try:
        r = http.get(f"{TMDB_BASE}{path}",
                     headers={"Authorization": f"Bearer {TMDB_TOKEN}"},
                     params=params or {},
                     timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("TMDB %s failed: %s", path, e)
        return None


def tmdb_search_movie(title, year=None):
    p = {"query": title, "include_adult": "false"}
    if year:
        p["year"] = year
    j = _tmdb_get("/search/movie", p) or {}
    return (j.get("results") or [None])[0]


def tmdb_search_tv(title, year=None):
    p = {"query": title, "include_adult": "false"}
    if year:
        p["first_air_date_year"] = year
    j = _tmdb_get("/search/tv", p) or {}
    return (j.get("results") or [None])[0]


def tmdb_movie(tmdb_id):
    return _tmdb_get(f"/movie/{tmdb_id}")


def tmdb_tv(tmdb_id):
    return _tmdb_get(f"/tv/{tmdb_id}")


def tmdb_tv_season(tmdb_id, season_no):
    return _tmdb_get(f"/tv/{tmdb_id}/season/{season_no}")


def download_poster(poster_path, dest_dir):
    """Fetch a TMDB poster to disk (idempotent). poster_path is TMDB's
    `/xxx.jpg` prefix; we key the cache on it verbatim so a re-approve doesn't
    hit the CDN again."""
    if not poster_path:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    safe = poster_path.lstrip("/").replace("/", "_")
    dest = os.path.join(dest_dir, safe)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    try:
        r = http.get(f"{TMDB_IMG}{poster_path}", timeout=30, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return dest
    except Exception as e:
        log.warning("poster download failed: %s", e)
        return None


# ── Filename parse ───────────────────────────────────────────────────────────

def parse_filename(path):
    """Extract title/year/season/episode/etc. via guessit. Returns a dict
    with str/int values. Empty dict if guessit missing (nix module should
    always install it, but be defensive)."""
    p = Path(path)
    if guessit is None:
        # Last-resort fallback so the module still stages *something*.
        return {"title": p.stem, "type": "movie"}
    try:
        g = dict(guessit(p.name))
    except Exception as e:
        log.warning("guessit failed on %s: %s", p.name, e)
        return {"title": p.stem, "type": "movie"}
    out = {}
    if g.get("title"):
        out["title"] = str(g["title"])
    if g.get("year"):
        out["year"] = int(g["year"])
    if g.get("season") is not None:
        # guessit can return a list when the file references a range.
        s = g["season"]
        out["season"] = int(s[0]) if isinstance(s, list) else int(s)
    if g.get("episode") is not None:
        e = g["episode"]
        out["episode"] = int(e[0]) if isinstance(e, list) else int(e)
    if g.get("episode_title"):
        out["episode_title"] = str(g["episode_title"])
    # guessit says 'episode' when there's any S/E present; treat as show.
    out["type"] = ("show" if (out.get("season") is not None
                              or out.get("episode") is not None)
                   else "movie")
    return out


def _looks_like_sample(path):
    try:
        size_ok = path.stat().st_size < SAMPLE_MAX_BYTES
    except OSError:
        return False
    return size_ok and bool(SAMPLE_RE.search(path.name))


def list_video_files(folder):
    """All non-sample video files under `folder`, sorted."""
    p = Path(folder)
    if p.is_file():
        if p.suffix.lower() not in VIDEO_EXTS or _looks_like_sample(p):
            return []
        return [p]
    out = []
    for f in p.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() not in VIDEO_EXTS:
            continue
        if _looks_like_sample(f):
            log.info("skipping sample file: %s", f)
            continue
        out.append(f)
    return sorted(out)


# ── NFO fallback (Radarr/Sonarr sidecars) ────────────────────────────────────

_NFO_TMDB_RE = re.compile(r"<tmdbid>\s*(\d+)\s*</tmdbid>", re.IGNORECASE)
_NFO_IMDB_RE = re.compile(r"<imdb_?id>\s*(tt\d+)\s*</imdb_?id>", re.IGNORECASE)
_NFO_URL_TMDB_RE = re.compile(
    r"themoviedb\.org/(?:movie|tv)/(\d+)", re.IGNORECASE)
_NFO_URL_IMDB_RE = re.compile(r"imdb\.com/title/(tt\d+)", re.IGNORECASE)


def read_nfo(video_path):
    """Look for an .nfo sibling of the video and pull tmdb_id / imdb_id.
    Radarr/Sonarr NFOs are XML with <tmdbid>/<imdbid> tags; some scrapers
    only embed URLs, so we regex both. Returns {'tmdb_id':int|None,
    'imdb_id':str|None} or {} when no NFO is found."""
    video_path = Path(video_path)
    candidates = [
        video_path.with_suffix(".nfo"),
        video_path.parent / "movie.nfo",
        video_path.parent / "tvshow.nfo",
    ]
    for nfo in candidates:
        if not nfo.exists():
            continue
        try:
            body = nfo.read_text(errors="replace")
        except Exception:
            continue
        out = {}
        m = _NFO_TMDB_RE.search(body) or _NFO_URL_TMDB_RE.search(body)
        if m:
            try:
                out["tmdb_id"] = int(m.group(1))
            except ValueError:
                pass
        m = _NFO_IMDB_RE.search(body) or _NFO_URL_IMDB_RE.search(body)
        if m:
            out["imdb_id"] = m.group(1)
        if out:
            log.info("NFO hit for %s: %s", video_path.name, out)
            return out
    return {}


def tmdb_find_by_imdb(imdb_id):
    """TMDB /find lets us look up by external id. Returns the first movie or
    tv result, if any."""
    j = _tmdb_get(f"/find/{imdb_id}",
                  {"external_source": "imdb_id"}) or {}
    if j.get("movie_results"):
        return ("movie", j["movie_results"][0])
    if j.get("tv_results"):
        return ("tv", j["tv_results"][0])
    return (None, None)


# ── Subtype classification ───────────────────────────────────────────────────

def _is_anime(tmdb_detail):
    """TMDB rule: origin_country JP + Animation genre. Covers 95%+ of what a
    user would call anime. Chinese/Korean animation won't auto-classify -
    user can override via the subtype dropdown."""
    if not tmdb_detail:
        return False
    origin = tmdb_detail.get("origin_country") or []
    langs  = tmdb_detail.get("original_language")
    genre_ids = [g.get("id") for g in (tmdb_detail.get("genres") or [])]
    if "JP" in origin or langs == "ja":
        if TMDB_GENRE_ANIMATION in genre_ids:
            return True
    return False


def _is_documentary(tmdb_detail):
    if not tmdb_detail:
        return False
    genre_ids = [g.get("id") for g in (tmdb_detail.get("genres") or [])]
    return TMDB_GENRE_DOCUMENTARY in genre_ids


def classify_subtype(kind, tmdb_detail):
    """kind = 'movie' or 'show'. Returns one of:
      movie, show, anime_movie, anime_show, documentary, docuseries,
      short_film."""
    anime = _is_anime(tmdb_detail)
    doc   = _is_documentary(tmdb_detail)
    if kind == "movie":
        if anime:
            return "anime_movie"
        if doc:
            return "documentary"
        runtime = (tmdb_detail or {}).get("runtime")
        if runtime and runtime < SHORT_FILM_MAX_MINUTES:
            return "short_film"
        return "movie"
    # show
    if anime:
        return "anime_show"
    if doc:
        return "docuseries"
    return "show"


# ── Grouping ─────────────────────────────────────────────────────────────────

def _group_key(parsed):
    """Group episodes into (show_title_lower, season) buckets. Movies get a
    unique bucket per file so they stay 1-per-item."""
    if parsed.get("type") == "show":
        title = (parsed.get("title") or "").strip().lower()
        season = parsed.get("season") or 1
        return ("show", title, season)
    return ("movie", id(parsed))  # unique per parsed dict


def _extract_year(parsed_list):
    for p in parsed_list:
        if p.get("year"):
            return p["year"]
    return None


# ── Staging ──────────────────────────────────────────────────────────────────

def _stage_movie(file_path, parsed, folder):
    """One video row per movie file."""
    title = parsed.get("title") or Path(file_path).stem
    year  = parsed.get("year")

    # NFO takes precedence over guessit-title search - Radarr/Sonarr write
    # canonical IDs, and search-by-name mis-hits on ambiguous titles.
    nfo = read_nfo(file_path)
    tmdb_hit    = None
    tmdb_detail = None
    if tmdb_enabled():
        if nfo.get("tmdb_id"):
            tmdb_detail = tmdb_movie(nfo["tmdb_id"])
            if tmdb_detail:
                tmdb_hit = {"id": nfo["tmdb_id"]}
        elif nfo.get("imdb_id"):
            kind, hit = tmdb_find_by_imdb(nfo["imdb_id"])
            if kind == "movie" and hit:
                tmdb_hit = hit
                tmdb_detail = tmdb_movie(hit["id"])
        if not tmdb_detail:
            tmdb_hit    = tmdb_search_movie(title, year)
            tmdb_detail = tmdb_movie(tmdb_hit["id"]) if tmdb_hit else None
    subtype     = classify_subtype("movie", tmdb_detail)

    poster_local = None
    genre        = None
    overview     = None
    if tmdb_detail:
        title = tmdb_detail.get("title") or title
        rd    = tmdb_detail.get("release_date") or ""
        if rd[:4].isdigit():
            year = int(rd[:4])
        genres = [g.get("name") for g in tmdb_detail.get("genres") or []]
        if genres:
            genre = genres[0]
        overview = (tmdb_detail.get("overview") or "").strip()
        poster_local = download_poster(tmdb_detail.get("poster_path"),
                                       VIDEO_COVER_DIR)

    meta = {
        "kind":     "movie",
        "guessit":  parsed,
        "tmdb":     ({
            "id":       tmdb_detail.get("id"),
            "title":    tmdb_detail.get("title"),
            "year":     (tmdb_detail.get("release_date") or "")[:4],
            "genres":   [g.get("name") for g in tmdb_detail.get("genres") or []],
            "runtime":  tmdb_detail.get("runtime"),
            "overview": overview,
            "poster":   tmdb_detail.get("poster_path"),
            "origin":   tmdb_detail.get("origin_country"),
        } if tmdb_detail else None),
        "folder":   str(folder) if folder else None,
    }

    with db.get_db() as conn:
        cur = conn.execute(
            """INSERT OR REPLACE INTO items
                 (media_type, status, source_path, subtype,
                  title, year, genre, cover_local, meta_json, processed_at)
               VALUES ('video', 'ready', ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (str(file_path), subtype, title, year, genre, poster_local,
             json.dumps(meta)),
        )
        item_id = cur.lastrowid
    log.info("Staged movie id=%d: %s (%s) [%s]",
             item_id, title, year or "?", subtype)
    return item_id


def _stage_season(files_parsed, folder):
    """One item per (show, season) with each episode as a track row.
    files_parsed = list of (file_path, parsed_dict). All entries share the
    same show title + season."""
    first = files_parsed[0][1]
    show_title = first.get("title") or Path(files_parsed[0][0]).stem
    season_no  = first.get("season") or 1
    year_hint  = _extract_year([p for _, p in files_parsed])

    # NFO fallback (tvshow.nfo alongside the season folder).
    nfo = read_nfo(files_parsed[0][0])
    tmdb_hit    = None
    tmdb_detail = None
    if tmdb_enabled():
        if nfo.get("tmdb_id"):
            tmdb_detail = tmdb_tv(nfo["tmdb_id"])
            if tmdb_detail:
                tmdb_hit = {"id": nfo["tmdb_id"]}
        elif nfo.get("imdb_id"):
            kind, hit = tmdb_find_by_imdb(nfo["imdb_id"])
            if kind == "tv" and hit:
                tmdb_hit = hit
                tmdb_detail = tmdb_tv(hit["id"])
        if not tmdb_detail:
            tmdb_hit    = tmdb_search_tv(show_title, year_hint)
            tmdb_detail = tmdb_tv(tmdb_hit["id"]) if tmdb_hit else None
    subtype     = classify_subtype("show", tmdb_detail)

    show_year = year_hint
    genre     = None
    overview  = None
    poster_local = None
    if tmdb_detail:
        show_title = tmdb_detail.get("name") or show_title
        first_air  = tmdb_detail.get("first_air_date") or ""
        if first_air[:4].isdigit():
            show_year = int(first_air[:4])
        genres = [g.get("name") for g in tmdb_detail.get("genres") or []]
        if genres:
            genre = genres[0]
        overview = (tmdb_detail.get("overview") or "").strip()
        poster_local = download_poster(tmdb_detail.get("poster_path"),
                                       VIDEO_COVER_DIR)

    # Per-episode names come from the season endpoint.
    season_detail = None
    ep_by_no = {}
    if tmdb_detail and tmdb_hit:
        season_detail = tmdb_tv_season(tmdb_hit["id"], season_no)
        for ep in (season_detail or {}).get("episodes") or []:
            if ep.get("episode_number") is not None:
                ep_by_no[int(ep["episode_number"])] = ep

    display_title = f"{show_title} - Season {season_no:02d}"

    meta = {
        "kind":       "show",
        "show_title": show_title,
        "season_no":  season_no,
        "tmdb": ({
            "id":       tmdb_detail.get("id"),
            "name":     tmdb_detail.get("name"),
            "year":     (tmdb_detail.get("first_air_date") or "")[:4],
            "genres":   [g.get("name") for g in tmdb_detail.get("genres") or []],
            "overview": overview,
            "poster":   tmdb_detail.get("poster_path"),
            "origin":   tmdb_detail.get("origin_country"),
        } if tmdb_detail else None),
        "folder":     str(folder) if folder else None,
    }

    # Synthetic source key: one item per season. Include folder for
    # uniqueness across separate season downloads of the same show.
    show_slug = re.sub(r"\W+", "-", (show_title or "unknown").lower()).strip("-")
    source_key = f"{folder}#s{season_no:02d}#{show_slug}"

    with db.get_db() as conn:
        cur = conn.execute(
            """INSERT OR REPLACE INTO items
                 (media_type, status, source_path, subtype,
                  title, year, genre, cover_local, meta_json, processed_at)
               VALUES ('video', 'ready', ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (source_key, subtype, display_title, show_year, genre,
             poster_local, json.dumps(meta)),
        )
        item_id = cur.lastrowid
        conn.execute("DELETE FROM tracks WHERE item_id = ?", (item_id,))
        for fp, parsed in sorted(files_parsed,
                                 key=lambda x: x[1].get("episode") or 0):
            ep_no = parsed.get("episode")
            ep_title = parsed.get("episode_title")
            if not ep_title and ep_no in ep_by_no:
                ep_title = ep_by_no[ep_no].get("name")
            # Reuse the tracks table: track_no = episode, disc_no = season.
            conn.execute(
                """INSERT INTO tracks
                     (item_id, source_path, track_no, disc_no, title)
                   VALUES (?, ?, ?, ?, ?)""",
                (item_id, str(fp), ep_no, season_no, ep_title),
            )

    log.info("Staged show id=%d: %s [%s] (%d eps)",
             item_id, display_title, subtype, len(files_parsed))
    return item_id


def process_video(folder):
    """Scanner entry point. Walk folder, group into movies + show seasons,
    stage one item per group."""
    files = list_video_files(folder)
    if not files:
        log.warning("no video files in %s", folder)
        return None

    parsed_by_path = [(f, parse_filename(f)) for f in files]

    groups = defaultdict(list)
    for fp, parsed in parsed_by_path:
        groups[_group_key(parsed)].append((fp, parsed))

    last_id = None
    for key, entries in groups.items():
        if key[0] == "show":
            last_id = _stage_season(entries, folder)
        else:
            fp, parsed = entries[0]
            last_id = _stage_movie(fp, parsed, folder)
    return last_id


def process_video_file(path):
    """Single-file entry used by RETRY/REPROCESS when the item's source_path
    is a single file (movies). Show seasons are re-processed at the folder
    level via the containing meta['folder'] - the app route handles that."""
    p = Path(path)
    if not p.exists():
        return None
    parsed = parse_filename(p)
    if parsed.get("type") == "show":
        # Re-process as a one-episode season for this show/season.
        return _stage_season([(p, parsed)], p.parent)
    return _stage_movie(p, parsed, p.parent)


# ── Approval / write-out ─────────────────────────────────────────────────────

def _safe_path(s):
    if not s:
        return "_"
    s = re.sub(r'[<>:"|?*\\\\/]', "", s).strip()
    return s or "_"


def library_path_for(item, tracks=None):
    """Where the item will land after approve. Uses the item's subtype to
    look up the right target root.
      - Movies: <target>/<Title> (<Year>)/<Title> (<Year>).ext
      - Shows:  <target>/<Show> (<Year>)/Season <NN>/  (folder)"""
    subtype = item.get("subtype") or "movie"
    root = targets.target_for(subtype)
    title = _safe_path(item.get("title") or "Unknown")
    year  = item.get("year")

    meta = item.get("meta_json") or "{}"
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    if meta.get("kind") == "show":
        show = _safe_path(meta.get("show_title") or title)
        show_dir = f"{show} ({year})" if year else show
        season   = meta.get("season_no") or 1
        return Path(root) / show_dir / f"Season {int(season):02d}"

    # Movie
    stem = f"{title} ({year})" if year else title
    # Extension only known at write time - use the source file's ext.
    src = Path(item["source_path"])
    return Path(root) / stem / f"{stem}{src.suffix.lower()}"


_SXXEYY_RE = re.compile(r"[Ss](\d{1,2})[Ee](\d{1,3})")


def _sxxeyy(name):
    m = _SXXEYY_RE.search(name or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _find_subs_folder(src_dir):
    """Return the first sibling folder that looks like a subtitle dump. Some
    releases nest them (`Movie/Subs/`), and multi-episode packs commonly ship
    `Subs/` at the season root."""
    for name in ("Subs", "subs", "Subtitles", "subtitles"):
        cand = src_dir / name
        if cand.is_dir():
            return cand
    return None


def _copy_sidecars(src_file, dest_file):
    """Copy subtitles / nfo / artwork sitting next to the source video into
    the destination folder. Two paths:
      1. Siblings whose stem starts with the video stem (Sonarr layout).
      2. Files under an adjacent `Subs/` folder that share the video's
         SxxEyy tag OR - for movies with no such tag - copy every subtitle
         under Subs/ verbatim."""
    src  = Path(src_file)
    dest = Path(dest_file)

    # 1. Sibling stem match
    for f in src.parent.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in SIDECAR_EXTS:
            continue
        if not f.stem.startswith(src.stem):
            continue
        try:
            new = dest.parent / (dest.stem + f.name[len(src.stem):])
            shutil.copy2(f, new)
        except Exception as e:
            log.warning("sidecar copy failed %s: %s", f, e)

    # 2. Subs/ folder match
    subs_dir = _find_subs_folder(src.parent)
    if not subs_dir:
        return
    video_sxx = _sxxeyy(src.name)
    for sub in subs_dir.rglob("*"):
        if not sub.is_file():
            continue
        if sub.suffix.lower() not in SUBTITLE_EXTS:
            continue
        if video_sxx:
            # Episode: only pick subs whose own name (or ancestor folder
            # name) tags the same SxxEyy.
            ancestry = "/".join([sub.name] + [p.name for p in sub.parents])
            sub_sxx = _sxxeyy(ancestry)
            if sub_sxx != video_sxx:
                continue
        # Preserve language hint if present (`.en.srt`, `English.srt`).
        lang_hint = ""
        parts = sub.stem.split(".")
        if len(parts) > 1 and len(parts[-1]) in (2, 3):
            lang_hint = "." + parts[-1].lower()
        elif sub.stem.lower() in ("english", "spanish", "french", "german",
                                   "japanese", "chinese"):
            lang_hint = "." + sub.stem.lower()[:2]
        new = dest.parent / f"{dest.stem}{lang_hint}{sub.suffix.lower()}"
        try:
            shutil.copy2(sub, new)
        except Exception as e:
            log.warning("Subs/ copy failed %s: %s", sub, e)


def write_and_move(item, tracks=None, fetch_subs=False):
    """Approve pathway. For movies: move the file. For shows: move each
    episode into <show>/Season NN/<show> - SxxEyy - <title>.ext. When
    fetch_subs is True, hit OpenSubtitles for each landed video."""
    meta = item.get("meta_json") or "{}"
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    subtype = item.get("subtype") or "movie"
    root    = targets.target_for(subtype)
    title   = _safe_path(item.get("title") or "Unknown")
    year    = item.get("year")
    tmdb    = meta.get("tmdb") or {}
    tmdb_id = tmdb.get("id")

    # ── Show ── move each episode into a Jellyfin-style season folder.
    if meta.get("kind") == "show":
        show = _safe_path(meta.get("show_title") or title)
        show_dir = f"{show} ({year})" if year else show
        season   = int(meta.get("season_no") or 1)
        dest_dir = Path(root) / show_dir / f"Season {season:02d}"
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Poster sidecar at the show root (Jellyfin picks up poster.jpg).
        if item.get("cover_local") and os.path.exists(item["cover_local"]):
            try:
                with open(item["cover_local"], "rb") as s, \
                     open(dest_dir.parent / "poster.jpg", "wb") as d:
                    d.write(s.read())
            except Exception as e:
                log.warning("copy show poster failed: %s", e)

        track_paths = {}
        last_dest   = None
        for t in tracks or []:
            src = Path(t["source_path"])
            if not src.exists():
                log.warning("episode source missing: %s", src)
                continue
            ep_no    = t.get("track_no") or 0
            ep_title = t.get("title") or ""
            base = f"{show} - S{season:02d}E{int(ep_no):02d}"
            if ep_title:
                base += f" - {_safe_path(ep_title)}"
            dest = dest_dir / f"{base}{src.suffix.lower()}"
            try:
                src.replace(dest)
                _copy_sidecars(src, dest)
                track_paths[t["id"]] = str(dest)
                last_dest = dest
            except Exception as e:
                log.error("move failed %s -> %s: %s", src, dest, e)
                raise

            if fetch_subs and tmdb_id:
                try:
                    subtitles.fetch_for_video(
                        dest,
                        parent_tmdb_id=tmdb_id,
                        season_no=season,
                        episode_no=int(ep_no) if ep_no else None,
                    )
                except Exception:
                    log.exception("subtitle fetch failed for %s", dest)

        # Clean up an empty download folder
        folder = meta.get("folder")
        if folder and Path(folder).exists() and not any(Path(folder).iterdir()):
            try:
                Path(folder).rmdir()
            except Exception:
                pass

        return {"dest": str(last_dest or dest_dir), "track_paths": track_paths}

    # ── Movie ── one file in, one file out.
    src = Path(item["source_path"])
    if not src.exists():
        raise FileNotFoundError(src)

    stem = f"{title} ({year})" if year else title
    dest_dir = Path(root) / stem
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{stem}{src.suffix.lower()}"

    # Poster
    if item.get("cover_local") and os.path.exists(item["cover_local"]):
        try:
            with open(item["cover_local"], "rb") as s, \
                 open(dest_dir / "poster.jpg", "wb") as d:
                d.write(s.read())
        except Exception as e:
            log.warning("copy movie poster failed: %s", e)

    try:
        src.replace(dest)
    except Exception as e:
        log.error("move failed %s -> %s: %s", src, dest, e)
        raise

    _copy_sidecars(src, dest)

    if fetch_subs and tmdb_id:
        try:
            subtitles.fetch_for_video(dest, tmdb_id=tmdb_id)
        except Exception:
            log.exception("subtitle fetch failed for %s", dest)

    # Clean up an empty parent (if this was a one-file bundle)
    try:
        parent = Path(item["source_path"]).parent
        if (parent.exists() and str(parent) != root
                and not any(parent.iterdir())):
            parent.rmdir()
    except Exception:
        pass

    return {"dest": str(dest)}
