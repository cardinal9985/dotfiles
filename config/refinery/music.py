"""Music processor: detect album in a folder, read existing tags via mutagen,
look up canonical info on MusicBrainz + Bandcamp, download highest-resolution
cover art, normalize genre. Stages an item row in the DB for the approval UI."""

import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import quote_plus

import mutagen
import requests as http

import db
import genres

log = logging.getLogger("refinery.music")

MUSIC_EXTS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wma", ".wav",
              ".alac", ".aiff", ".aif"}

COVER_DIR = os.environ.get("REFINERY_COVER_DIR", "/persist/refinery/covers")

MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
BC_BASE = "https://bandcamp.com"

USER_AGENT = "ishimura-refinery/1.0 (https://refinery.ishimura.lol)"


def _http_get(url, params=None, headers=None, timeout=15):
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    try:
        r = http.get(url, params=params, headers=h, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        log.warning("HTTP %s failed: %s", url, e)
        return None


# ── Existing tag extraction ──────────────────────────────────────────────────

def _list_audio_files(folder):
    return sorted(
        p for p in Path(folder).rglob("*")
        if p.is_file() and p.suffix.lower() in MUSIC_EXTS
    )


def _read_tag(audio, *keys):
    """Try a list of tag keys, return first non-empty string value."""
    for k in keys:
        v = audio.tags.get(k) if audio.tags else None
        if v:
            if hasattr(v, "text"):           # ID3 frames
                v = v.text
            if isinstance(v, list):
                v = v[0] if v else None
            if v:
                return str(v).strip()
    return None


def read_existing_metadata(folder):
    """Scan an album folder, return aggregated tags from the actual files."""
    files = _list_audio_files(folder)
    if not files:
        return None

    tracks = []
    album_tags = {}
    genre_tags = []
    bandcamp_url = None

    for path in files:
        try:
            audio = mutagen.File(path, easy=True)
        except Exception as e:
            log.warning("mutagen failed on %s: %s", path, e)
            continue
        if audio is None:
            continue
        tags = audio.tags or {}

        track_no = _read_tag(audio, "tracknumber")
        disc_no  = _read_tag(audio, "discnumber") or "1"
        title    = _read_tag(audio, "title")
        artist   = _read_tag(audio, "artist")
        album    = _read_tag(audio, "album")
        album_artist = _read_tag(audio, "albumartist") or artist
        year     = _read_tag(audio, "date", "year")
        genre    = _read_tag(audio, "genre")
        comment  = _read_tag(audio, "comment")

        # Bandcamp puts the album URL in the COMMENT/description field
        if comment and "bandcamp.com" in comment and not bandcamp_url:
            m = re.search(r"https?://[\w.-]+\.bandcamp\.com/[\w/-]+", comment)
            if m:
                bandcamp_url = m.group(0)

        if genre:
            genre_tags.append(genre)

        duration = int(audio.info.length) if audio.info else None

        try:
            tn = int(re.sub(r"[^\d].*", "", track_no)) if track_no else None
        except Exception:
            tn = None
        try:
            dn = int(re.sub(r"[^\d].*", "", disc_no)) if disc_no else 1
        except Exception:
            dn = 1

        tracks.append({
            "source_path": str(path),
            "track_no": tn,
            "disc_no": dn,
            "title": title,
            "duration_secs": duration,
        })

        # Album-level: first non-empty wins (assume consistent across files)
        if album and "album" not in album_tags:
            album_tags["album"] = album
        if album_artist and "artist" not in album_tags:
            album_tags["artist"] = album_artist
        if year and "year" not in album_tags:
            album_tags["year"] = year

    if not tracks:
        return None

    return {
        "album":        album_tags.get("album"),
        "artist":       album_tags.get("artist"),
        "year":         album_tags.get("year"),
        "genre_tags":   genre_tags,
        "bandcamp_url": bandcamp_url,
        "tracks":       tracks,
    }


# ── MusicBrainz lookup ───────────────────────────────────────────────────────

def lookup_musicbrainz(artist, album):
    if not (artist and album):
        return None
    r = _http_get(f"{MB_BASE}/release/", params={
        "query": f'artist:"{artist}" AND release:"{album}"',
        "fmt": "json",
        "limit": 5,
    })
    if not r:
        return None
    data = r.json()
    rels = data.get("releases") or []
    if not rels:
        return None
    rel = rels[0]
    return {
        "mb_release_id": rel.get("id"),
        "title":         rel.get("title"),
        "year":          (rel.get("date") or "")[:4],
        "country":       rel.get("country"),
    }


def cover_art_archive_url(mb_release_id):
    """Front cover URL for a MusicBrainz release ID, or None."""
    if not mb_release_id:
        return None
    r = _http_get(f"{CAA_BASE}/release/{mb_release_id}")
    if not r:
        return None
    try:
        for img in r.json().get("images", []):
            if img.get("front"):
                return img.get("image")
    except Exception:
        pass
    return None


# ── Bandcamp lookup (scrape) ─────────────────────────────────────────────────

_BC_JSONLD_RE = re.compile(
    r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
    re.DOTALL,
)


def bandcamp_search(artist, album):
    """Find a likely Bandcamp album URL for (artist, album)."""
    if not (artist and album):
        return None
    q = quote_plus(f"{artist} {album}")
    r = _http_get(f"{BC_BASE}/search", params={"q": f"{artist} {album}",
                                                "item_type": "a"})
    if not r:
        return None
    # search results contain <a class="artcont" href="https://...">
    m = re.search(r'<a class="artcont"[^>]*href="(https://[^"]+)"', r.text)
    return m.group(1) if m else None


def bandcamp_album(url):
    """Fetch and parse a Bandcamp album page. Returns {title, artist, year,
    cover_url, tags, tracks}."""
    if not url:
        return None
    r = _http_get(url)
    if not r:
        return None
    m = _BC_JSONLD_RE.search(r.text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except Exception:
        return None

    name = data.get("name")
    by   = (data.get("byArtist") or {}).get("name")
    pub  = (data.get("datePublished") or "")[:4]
    img  = data.get("image")
    # Bandcamp `image` is usually 350px (`_16.jpg`). Bump to 1500px (`_10.jpg`).
    if img:
        img = re.sub(r"_\d+\.jpg$", "_10.jpg", img)

    tags = (data.get("keywords") or "").split(", ") if data.get("keywords") else []

    # Track list from JSON-LD
    tracks = []
    tr = data.get("track") or {}
    items = tr.get("itemListElement") or []
    for it in items:
        t = it.get("item") or {}
        tracks.append({
            "track_no": it.get("position"),
            "title":    t.get("name"),
            "duration_secs": _bc_duration_to_secs(t.get("duration")),
        })

    return {
        "url":       url,
        "title":     name,
        "artist":    by,
        "year":      pub,
        "cover_url": img,
        "tags":      [t for t in tags if t],
        "tracks":    tracks,
    }


def _bc_duration_to_secs(iso):
    """Parse ISO 8601 duration like 'P00H04M12S' to seconds."""
    if not iso:
        return None
    m = re.match(r"P(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", iso)
    if not m:
        return None
    h, mi, s = m.groups()
    return int((int(h or 0) * 3600 + int(mi or 0) * 60 + float(s or 0)))


# ── Cover art download ───────────────────────────────────────────────────────

def download_cover(url, dest_dir):
    """Download cover to dest_dir, return local path or None."""
    if not url:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    name = re.sub(r"[^\w.-]", "_", url.split("/")[-1])[:120]
    if "." not in name:
        name += ".jpg"
    path = os.path.join(dest_dir, name)
    try:
        r = http.get(url, headers={"User-Agent": USER_AGENT},
                     timeout=30, stream=True)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return path
    except Exception as e:
        log.warning("cover download failed %s: %s", url, e)
        return None


# ── Top-level processing ─────────────────────────────────────────────────────

def process_album(folder):
    """Read folder, merge MB + Bandcamp + embedded data, insert a 'ready' item
    row into the DB for the approval UI."""
    log.info("Processing music album: %s", folder)
    existing = read_existing_metadata(folder)
    if not existing or not existing["tracks"]:
        log.warning("No audio files in %s, skipping", folder)
        return None

    artist = existing.get("artist")
    album  = existing.get("album")
    year   = existing.get("year")

    # Cross-source lookups
    mb = lookup_musicbrainz(artist, album)
    bc_url = existing.get("bandcamp_url") or bandcamp_search(artist, album)
    bc = bandcamp_album(bc_url) if bc_url else None

    # Merge with preference rules
    final_year   = (mb and mb.get("year")) or (bc and bc.get("year")) or year
    cover_url    = (bc and bc.get("cover_url")) or (
                    mb and cover_art_archive_url(mb["mb_release_id"]))

    # Aggregate genre tags from all sources, normalize to one bucket
    genre_pool = list(existing.get("genre_tags") or [])
    if bc and bc.get("tags"):
        genre_pool.extend(bc["tags"])
    genre = genres.normalize(genre_pool)

    # Per-track titles: prefer MusicBrainz/Bandcamp ordered list if available,
    # else fall back to embedded titles.
    tracks = list(existing["tracks"])
    if bc and bc.get("tracks"):
        # Match by track number where possible
        bc_by_num = {t["track_no"]: t for t in bc["tracks"] if t.get("track_no")}
        for t in tracks:
            if t.get("track_no") and t["track_no"] in bc_by_num:
                bc_t = bc_by_num[t["track_no"]]
                if bc_t.get("title"):
                    t["title_suggestion"] = bc_t["title"]

    cover_local = download_cover(cover_url, COVER_DIR) if cover_url else None

    meta = {
        "embedded":     existing,
        "musicbrainz":  mb,
        "bandcamp":     bc,
        "bandcamp_url": bc_url,
    }

    with db.get_db() as conn:
        cur = conn.execute(
            """INSERT OR REPLACE INTO items
                 (media_type, status, source_path, title, artist, year, genre,
                  cover_url, cover_local, meta_json, processed_at)
               VALUES ('music', 'ready', ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (str(folder), album, artist,
             int(final_year) if str(final_year).isdigit() else None,
             genre, cover_url, cover_local, json.dumps(meta)),
        )
        item_id = cur.lastrowid
        # Clear any old tracks for this item (re-process case)
        conn.execute("DELETE FROM tracks WHERE item_id = ?", (item_id,))
        for t in tracks:
            conn.execute(
                """INSERT INTO tracks
                     (item_id, source_path, track_no, disc_no, title, duration_secs)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item_id, t["source_path"], t.get("track_no"),
                 t.get("disc_no") or 1,
                 t.get("title_suggestion") or t.get("title"),
                 t.get("duration_secs")),
            )

    log.info("Staged music album id=%d: %s - %s", item_id, artist, album)
    return item_id


# ── Approval / write-out ─────────────────────────────────────────────────────

def _safe_path(s):
    """Strip filesystem-hostile characters from a path segment."""
    if not s:
        return "_"
    s = re.sub(r'[<>:"|?*\\\\/]', "", s).strip()
    return s or "_"


def write_and_move(item, tracks, target_root):
    """Write final tags to the source files, then move them into the Navidrome
    library under Artist/YYYY - Album/NN - Track.ext."""
    artist_dir = _safe_path(item["artist"] or "Unknown Artist")
    album_dir  = "{} - {}".format(
        item["year"] or "0000",
        _safe_path(item["title"] or "Unknown Album"),
    )
    dest_album = Path(target_root) / artist_dir / album_dir
    dest_album.mkdir(parents=True, exist_ok=True)

    # Stash cover.jpg next to tracks
    if item["cover_local"] and os.path.exists(item["cover_local"]):
        try:
            with open(item["cover_local"], "rb") as src, \
                 open(dest_album / "cover.jpg", "wb") as dst:
                dst.write(src.read())
        except Exception as e:
            log.warning("copy cover failed: %s", e)

    for t in tracks:
        src = Path(t["source_path"])
        if not src.exists():
            log.warning("source missing: %s", src)
            continue

        # Update tags before move
        try:
            audio = mutagen.File(str(src), easy=True)
            if audio is not None:
                if audio.tags is None:
                    audio.add_tags()
                audio.tags["artist"]      = item["artist"] or ""
                audio.tags["albumartist"] = item["artist"] or ""
                audio.tags["album"]       = item["title"]  or ""
                audio.tags["title"]       = t["title"]     or src.stem
                if item["year"]:
                    audio.tags["date"] = str(item["year"])
                if item["genre"]:
                    audio.tags["genre"] = item["genre"]
                if t.get("track_no"):
                    audio.tags["tracknumber"] = str(t["track_no"])
                if t.get("disc_no"):
                    audio.tags["discnumber"] = str(t["disc_no"])
                audio.save()
        except Exception as e:
            log.warning("tag write failed %s: %s", src, e)

        # Build target filename
        tn = "{:02d}".format(t["track_no"]) if t.get("track_no") else "00"
        title = _safe_path(t["title"] or src.stem)
        dest = dest_album / f"{tn} - {title}{src.suffix.lower()}"
        try:
            src.replace(dest)
        except Exception as e:
            log.error("move failed %s -> %s: %s", src, dest, e)

    return str(dest_album)
