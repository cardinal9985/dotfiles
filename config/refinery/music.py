"""Music processor: detect album in a folder, read existing tags via mutagen,
look up canonical info on MusicBrainz + Bandcamp, download highest-resolution
cover art, normalize genre. Stages an item row in the DB for the approval UI."""

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import quote_plus

import mutagen
import requests as http


# ── Per-service rate limiting ─────────────────────────────────────────────────
# Protects parallel workers from blowing past upstream rate limits. MB is
# strict (1 req/s anonymous); others get a polite throttle.
_rate_locks = {}
_rate_state = {}


def _rate_limited(service, min_interval_secs=1.0):
    """Block until at least `min_interval_secs` has elapsed since the last
    call for this service (process-wide)."""
    lock = _rate_locks.setdefault(service, threading.Lock())
    with lock:
        last = _rate_state.get(service, 0.0)
        elapsed = time.time() - last
        if elapsed < min_interval_secs:
            time.sleep(min_interval_secs - elapsed)
        _rate_state[service] = time.time()

import db
import genres
import quality

log = logging.getLogger("refinery.music")

MUSIC_EXTS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wma", ".wav",
              ".alac", ".aiff", ".aif"}

COVER_DIR        = os.environ.get("REFINERY_COVER_DIR",        "/persist/refinery/covers")
SPECTROGRAM_DIR  = os.environ.get("REFINERY_SPECTROGRAM_DIR",  "/persist/refinery/spectrograms")
ARTIST_PHOTO_DIR = os.environ.get("REFINERY_ARTIST_PHOTO_DIR", "/persist/refinery/artists")

# If set, copy files into the library instead of moving them out of the
# source inbox. Useful for testing or if you want to keep the original.
KEEP_SOURCE = os.environ.get("REFINERY_KEEP_SOURCE", "0") not in ("", "0", "false", "False")

MB_BASE  = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
BC_BASE  = "https://bandcamp.com"
LB_BASE  = "https://api.listenbrainz.org/1"
LFM_BASE = "https://ws.audioscrobbler.com/2.0/"
LRC_BASE = "https://lrclib.net/api"

LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "")

USER_AGENT = "ishimura-refinery/1.0 (https://refinery.ishimura.lol)"

# Title-cleaning regexes - shared by lrclib_get fallback chain, ROM tag
# stripping, etc.
_PARENS_RE    = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
_DASH_TAIL_RE = re.compile(r"\s+-\s+.*$")
_FEAT_RE      = re.compile(r"\s+(feat\.?|ft\.?|featuring|with)\s+.*$",
                            re.IGNORECASE)


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
        mb_album_id = _read_tag(audio, "musicbrainz_albumid")
        if mb_album_id and "mb_album_id" not in album_tags:
            album_tags["mb_album_id"] = mb_album_id

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
            dn = int(re.sub(r"[^\d].*", "", disc_no)) if disc_no else None
        except Exception:
            dn = None

        # Fall back to "CD 1" / "Disc 02" style subfolders when the file
        # itself has no disc tag.
        if not dn:
            dn = _disc_from_path(path, folder) or 1

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
        "mb_album_id":  album_tags.get("mb_album_id"),
        "genre_tags":   genre_tags,
        "bandcamp_url": bandcamp_url,
        "tracks":       tracks,
    }


# ── MusicBrainz lookup ───────────────────────────────────────────────────────

def lookup_musicbrainz(artist, album):
    if not (artist and album):
        return None
    _rate_limited("musicbrainz")
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
    rg  = rel.get("release-group") or {}
    return {
        "mb_release_id":       rel.get("id"),
        "mb_release_group_id": rg.get("id"),
        "title":               rel.get("title"),
        "year":                (rel.get("date") or "")[:4],
        "country":             rel.get("country"),
    }


def lookup_musicbrainz_by_id(mb_release_id):
    """Direct MB release lookup by MBID. Skips the slow search-by-name path.
    Used during reimport when files already have musicbrainz_albumid tagged
    (every file in a properly-tagged Navidrome library has this).
    inc=release-groups so we can hand the release-group MBID to ListenBrainz
    later (LB tag queries are release-group-scoped, not release-scoped)."""
    if not mb_release_id:
        return None
    _rate_limited("musicbrainz")
    r = _http_get(f"{MB_BASE}/release/{mb_release_id}",
                  params={"fmt": "json", "inc": "release-groups"})
    if not r:
        return None
    try:
        data = r.json()
    except Exception:
        return None
    rg = data.get("release-group") or {}
    return {
        "mb_release_id":       data.get("id"),
        "mb_release_group_id": rg.get("id"),
        "title":               data.get("title"),
        "year":                (data.get("date") or "")[:4],
        "country":             data.get("country"),
    }


def cover_art_archive_url(mb_release_id):
    """Front cover URL for a MusicBrainz release ID, or None."""
    if not mb_release_id:
        return None
    _rate_limited("coverartarchive", 0.5)
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
    _rate_limited("bandcamp", 1.0)
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
    _rate_limited("bandcamp", 1.0)
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


# ── Last.fm cross-check ──────────────────────────────────────────────────────

def lastfm_album_info(artist, album):
    """Last.fm album.getInfo - useful for tags + release year + cover."""
    if not (LASTFM_API_KEY and artist and album):
        return None
    r = _http_get(LFM_BASE, params={
        "method":   "album.getinfo",
        "artist":   artist,
        "album":    album,
        "api_key":  LASTFM_API_KEY,
        "format":   "json",
        "autocorrect": "1",
    })
    if not r:
        return None
    a = (r.json() or {}).get("album") or {}
    tags = [t.get("name") for t in
            ((a.get("tags") or {}).get("tag") or []) if t.get("name")]
    # Last.fm images list - pick the largest
    imgs = a.get("image") or []
    cover = ""
    for img in reversed(imgs):  # largest is last
        if img.get("#text"):
            cover = img["#text"]
            break
    return {
        "artist":    a.get("artist"),
        "title":     a.get("name"),
        "url":       a.get("url"),
        "mbid":      a.get("mbid"),
        "tags":      tags,
        "cover_url": cover or None,
    }


# ── ListenBrainz cross-check ─────────────────────────────────────────────────

def listenbrainz_release_lookup(mb_release_group_id):
    """ListenBrainz tag lookup, keyed by the MusicBrainz release-GROUP MBID
    (not release MBID - they're different). Endpoint is a bulk-style GET
    that wraps results under the MBID key."""
    if not mb_release_group_id:
        return None
    r = _http_get(f"{LB_BASE}/metadata/release_group/", params={
        "release_group_mbids": mb_release_group_id,
        "inc":                 "tag",
    })
    if not r:
        return None
    data    = (r.json() or {}).get(mb_release_group_id) or {}
    tag_obj = data.get("tag") or {}
    tags    = []
    for level in ("release_group", "artist"):
        for t in (tag_obj.get(level) or []):
            if t.get("tag"):
                tags.append(t["tag"])
    return {"tags": tags}


# ── Lyrics (LRCLib) ──────────────────────────────────────────────────────────

def lrclib_get(artist, track, album=None, duration=None):
    """Fetch synced + plain lyrics from LRCLib for one track. LRCLib's /get
    is exact-match, so we try a couple of cleaned-up variants and finally
    fall back to the fuzzy /search endpoint. Returns {synced, plain} dict
    or None."""
    if not (artist and track):
        return None

    def _try_get(t, a=None):
        params = {"artist_name": artist, "track_name": t}
        if a:
            params["album_name"] = a
        if duration:
            params["duration"] = int(duration)
        r = _http_get(f"{LRC_BASE}/get", params=params)
        if not r:
            return None
        d = r.json() or {}
        if d.get("syncedLyrics") or d.get("plainLyrics"):
            return {
                "synced": (d.get("syncedLyrics") or "").strip(),
                "plain":  (d.get("plainLyrics")  or "").strip(),
            }
        return None

    # 1) exact match as-is
    result = _try_get(track, album)
    if result:
        return result

    # 2) strip parenthesized / "- Remastered" / "feat" tails, retry
    cleaned = _PARENS_RE.sub("", track)
    cleaned = _DASH_TAIL_RE.sub("", cleaned)
    cleaned = _FEAT_RE.sub("", cleaned).strip()
    if cleaned and cleaned.lower() != track.lower():
        result = _try_get(cleaned, album)
        if result:
            return result

    # 3) fuzzy /search fallback - returns a ranked list, pick top hit that
    # has actual lyrics
    r = _http_get(f"{LRC_BASE}/search", params={
        "artist_name": artist,
        "track_name":  cleaned or track,
    })
    if not r:
        return None
    try:
        items = r.json() or []
    except Exception:
        return None
    for it in items[:5]:
        if it.get("syncedLyrics") or it.get("plainLyrics"):
            return {
                "synced": (it.get("syncedLyrics") or "").strip(),
                "plain":  (it.get("plainLyrics")  or "").strip(),
            }
    return None


# ── Multi-disc folder detection ──────────────────────────────────────────────

_DISC_FOLDER_RE = re.compile(
    r"^\s*(?:cd|disc|disk)\s*0*(\d+)\b",
    re.IGNORECASE,
)


def _disc_from_path(audio_path, album_root):
    """If the file lives inside a 'CD 1' / 'Disc 02' / etc. subfolder of the
    album root, return that disc number. Otherwise None."""
    rel = Path(audio_path).relative_to(album_root)
    for part in rel.parts[:-1]:
        m = _DISC_FOLDER_RE.match(part)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


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


def extract_embedded_cover(audio_paths, dest_dir):
    """Last-resort cover source for obscure releases that aren't on MB /
    Bandcamp / Last.fm: pull the first embedded picture out of any track.
    Handles FLAC pictures, MP3 APIC, and M4A covr."""
    if not audio_paths:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    for ap in audio_paths:
        try:
            audio = mutagen.File(ap)
        except Exception:
            continue
        if not audio:
            continue

        data = mime = None

        # FLAC (and OGG via metadata_block_picture)
        pics = getattr(audio, "pictures", None)
        if pics:
            data, mime = pics[0].data, (pics[0].mime or "image/jpeg")

        # MP3 ID3 APIC
        if not data and audio.tags is not None:
            try:
                apics = audio.tags.getall("APIC") if hasattr(audio.tags, "getall") else []
                if apics:
                    data, mime = apics[0].data, (apics[0].mime or "image/jpeg")
            except Exception:
                pass

        # M4A 'covr' atom (mutagen.mp4.MP4Cover)
        if not data and audio.tags is not None:
            try:
                covr = audio.tags.get("covr")
                if covr:
                    c = covr[0]
                    # FORMAT_PNG = 14, FORMAT_JPEG = 13 (mutagen.mp4)
                    fmt = getattr(c, "imageformat", 13)
                    data, mime = bytes(c), ("image/png" if fmt == 14 else "image/jpeg")
            except Exception:
                pass

        if data:
            ext  = ".png" if "png" in (mime or "").lower() else ".jpg"
            key  = hashlib.sha1(data[:8192]).hexdigest()[:20]
            out  = os.path.join(dest_dir, f"embedded-{key}{ext}")
            if not os.path.exists(out):
                with open(out, "wb") as f:
                    f.write(data)
            log.info("extracted embedded cover from %s -> %s", ap, out)
            return out
    return None


# ── Artist photo (Deezer) ────────────────────────────────────────────────────

def fetch_artist_photo(artist):
    """Download highest-resolution artist photo from Deezer (free, no auth).
    Cached on disk so repeated albums by the same artist reuse the file."""
    if not artist:
        return None
    slug = re.sub(r"[^\w]+", "_", artist.lower()).strip("_")[:80] or "unknown"
    dest = os.path.join(ARTIST_PHOTO_DIR, f"{slug}.jpg")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    try:
        r = http.get("https://api.deezer.com/search/artist",
                     params={"q": artist, "limit": 1},
                     headers={"User-Agent": USER_AGENT}, timeout=10)
        r.raise_for_status()
        results = (r.json() or {}).get("data") or []
        if not results:
            return None
        img_url = (results[0].get("picture_xl")
                   or results[0].get("picture_big")
                   or results[0].get("picture_medium"))
        if not img_url:
            return None
        os.makedirs(ARTIST_PHOTO_DIR, exist_ok=True)
        img = http.get(img_url, headers={"User-Agent": USER_AGENT},
                       timeout=30, stream=True)
        img.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in img.iter_content(8192):
                f.write(chunk)
        return dest
    except Exception as e:
        log.warning("artist photo fetch failed for %s: %s", artist, e)
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

    # Single-track URLs (Bandcamp /track/X, single-video yt-dlp) have no
    # album tag - only title. Fall back to the track title so the queue UI
    # shows something useful instead of '?'.
    if not album and existing.get("tracks"):
        album = existing["tracks"][0].get("title")
    # Absolute last resort: the folder name.
    if not album:
        album = Path(str(folder)).name

    # Cross-source lookups. If the file already has a MusicBrainz album ID
    # (true for any properly tagged library), skip the search-by-name path
    # and go straight to /release/<id>. ~3x fewer MB calls per album.
    if existing.get("mb_album_id"):
        mb = lookup_musicbrainz_by_id(existing["mb_album_id"])
    else:
        mb = lookup_musicbrainz(artist, album)
    bc_url = existing.get("bandcamp_url") or bandcamp_search(artist, album)
    bc     = bandcamp_album(bc_url) if bc_url else None
    lfm    = lastfm_album_info(artist, album)
    lb     = listenbrainz_release_lookup(mb["mb_release_group_id"]) if mb else None

    # Merge with preference rules
    final_year = (mb and mb.get("year")) or (bc and bc.get("year")) or year
    # Cover: Bandcamp (1500px) > Cover Art Archive > Last.fm (variable)
    cover_url = (
        (bc and bc.get("cover_url")) or
        (mb and cover_art_archive_url(mb["mb_release_id"])) or
        (lfm and lfm.get("cover_url"))
    )

    # Aggregate genre tags from all sources, normalize to one bucket
    genre_pool = list(existing.get("genre_tags") or [])
    if bc  and bc.get("tags"):  genre_pool.extend(bc["tags"])
    if lfm and lfm.get("tags"): genre_pool.extend(lfm["tags"])
    if lb  and lb.get("tags"):  genre_pool.extend(lb["tags"])
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
    # Fall back to whatever is embedded in the audio files (yt-dlp's
    # --embed-thumbnail, Bandcamp's zip with covers, etc.) for obscure
    # releases not on MB/Bandcamp/Last.fm.
    if not cover_local:
        cover_local = extract_embedded_cover(
            [t["source_path"] for t in tracks], COVER_DIR
        )
    artist_photo_local = fetch_artist_photo(artist)

    # Generate spectrogram from the longest track (most likely to be a real
    # song rather than an intro/outro). One per album is enough for the
    # Soulseek-style "proof of lossless" share.
    spec_local = None
    longest = max(tracks, key=lambda t: t.get("duration_secs") or 0,
                  default=None)
    if longest:
        key = hashlib.sha1(str(folder).encode()).hexdigest()[:16]
        spec_path = os.path.join(SPECTROGRAM_DIR, f"{key}.png")
        if quality.generate_spectrogram(longest["source_path"], spec_path):
            spec_local = spec_path

    # Fetch lyrics per track (LRCLib is per-track, not per-album)
    for t in tracks:
        title = t.get("title_suggestion") or t.get("title")
        lyr = lrclib_get(artist, title, album, t.get("duration_secs"))
        if lyr:
            t["lyrics_synced"] = lyr.get("synced") or ""
            t["lyrics_plain"]  = lyr.get("plain")  or ""

        # Quality verification (FLAC integrity + spectral cutoff)
        q = quality.analyze(t["source_path"])
        t["quality_ok"]      = 1 if q["verified"] else 0
        t["quality_cutoff"]  = q["freq_cutoff_hz"]
        t["quality_verdict"] = q["verdict"]
        t["quality_error"]   = q.get("error")

    meta = {
        "embedded":     existing,
        "musicbrainz":  mb,
        "bandcamp":     bc,
        "bandcamp_url": bc_url,
        "lastfm":       lfm,
        "listenbrainz": lb,
    }

    with db.get_db() as conn:
        cur = conn.execute(
            """INSERT OR REPLACE INTO items
                 (media_type, status, source_path, title, artist, year, genre,
                  cover_url, cover_local, spectrogram_local,
                  artist_photo_local, meta_json, processed_at)
               VALUES ('music', 'ready', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       datetime('now'))""",
            (str(folder), album, artist,
             int(final_year) if str(final_year).isdigit() else None,
             genre, cover_url, cover_local, spec_local,
             artist_photo_local, json.dumps(meta)),
        )
        item_id = cur.lastrowid
        # Clear any old tracks for this item (re-process case)
        conn.execute("DELETE FROM tracks WHERE item_id = ?", (item_id,))
        for t in tracks:
            conn.execute(
                """INSERT INTO tracks
                     (item_id, source_path, track_no, disc_no, title,
                      duration_secs, lyrics_synced, lyrics_plain,
                      quality_ok, quality_cutoff, quality_verdict, quality_error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, t["source_path"], t.get("track_no"),
                 t.get("disc_no") or 1,
                 t.get("title_suggestion") or t.get("title"),
                 t.get("duration_secs"),
                 t.get("lyrics_synced"), t.get("lyrics_plain"),
                 t.get("quality_ok"), t.get("quality_cutoff"),
                 t.get("quality_verdict"), t.get("quality_error")),
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


def _is_compilation(tracks_per_artist):
    """Heuristic: if >= 3 distinct track artists across the album, treat as
    Various Artists compilation."""
    return len({a for a in tracks_per_artist if a}) >= 3


def library_path_for(target_root, artist, year, title):
    """The folder we'll write into. Used by the route to warn on conflict."""
    artist_dir = _safe_path(artist or "Unknown Artist")
    album_dir  = "{} - {}".format(year or "0000", _safe_path(title or "Unknown Album"))
    return Path(target_root) / artist_dir / album_dir


def _embed_cover(audio, cover_local):
    """Write cover art into the audio file's tags (FLAC pictures, ID3 APIC,
    M4A covr, etc.). mutagen handles the format-specific differences when we
    use its File() in non-easy mode."""
    if not cover_local or not os.path.exists(cover_local):
        return
    try:
        with open(cover_local, "rb") as f:
            data = f.read()
        mime = "image/png" if cover_local.lower().endswith(".png") else "image/jpeg"

        # Re-open without easy mode so we can write the picture frame
        path = audio.filename if hasattr(audio, "filename") else None
        if not path:
            return
        full = mutagen.File(path)
        if full is None:
            return

        if isinstance(full, mutagen.flac.FLAC):
            full.clear_pictures()
            pic = mutagen.flac.Picture()
            pic.type = 3  # cover (front)
            pic.mime = mime
            pic.data = data
            full.add_picture(pic)
            full.save()
        elif isinstance(full, mutagen.mp3.MP3):
            from mutagen.id3 import APIC
            full.tags.delall("APIC")
            full.tags.add(APIC(encoding=3, mime=mime, type=3,
                               desc="Cover", data=data))
            full.save()
        elif isinstance(full, mutagen.mp4.MP4):
            fmt = (mutagen.mp4.MP4Cover.FORMAT_PNG if mime == "image/png"
                   else mutagen.mp4.MP4Cover.FORMAT_JPEG)
            full.tags["covr"] = [mutagen.mp4.MP4Cover(data, imageformat=fmt)]
            full.save()
        # Other formats: skip silently
    except Exception as e:
        log.warning("embed cover failed: %s", e)


def _run_replaygain(folder):
    """Compute and write ReplayGain tags for everything in folder. Uses
    rsgain if present (handles MP3 + FLAC + Opus + M4A in one go)."""
    if not shutil.which("rsgain"):
        return
    try:
        subprocess.run(
            ["rsgain", "easy", str(folder)],
            check=False, capture_output=True, timeout=600,
        )
    except Exception as e:
        log.warning("rsgain failed for %s: %s", folder, e)


def write_and_move(item, tracks, target_root):
    """Write final tags to the source files, then move (or copy when
    REFINERY_KEEP_SOURCE is set) them into the Navidrome library under
    Artist/YYYY - Album/NN - Track.ext. Embeds cover art, writes MusicBrainz
    IDs, runs ReplayGain, and cleans up the empty source directory."""
    # Compilation detection - if a bunch of track artists differ from the
    # album-level "artist", file under "Various Artists" instead.
    track_artists = []
    for t in tracks:
        # Re-read each track's artist (not album_artist) from the source
        try:
            a = mutagen.File(t["source_path"], easy=True)
            if a and a.tags:
                v = a.tags.get("artist")
                if v:
                    track_artists.append(v[0] if isinstance(v, list) else str(v))
        except Exception:
            pass

    is_va = _is_compilation(track_artists)
    album_artist = "Various Artists" if is_va else (item["artist"] or "Unknown Artist")

    artist_dir = _safe_path(album_artist)
    album_dir  = "{} - {}".format(
        item["year"] or "0000",
        _safe_path(item["title"] or "Unknown Album"),
    )
    dest_album = Path(target_root) / artist_dir / album_dir
    dest_album.mkdir(parents=True, exist_ok=True)

    meta = json.loads(item.get("meta_json") or "{}") if isinstance(item.get("meta_json"), str) else (item.get("meta_json") or {})
    mb_release_id = (meta.get("musicbrainz") or {}).get("mb_release_id")

    # Stash cover.jpg next to tracks
    if item["cover_local"] and os.path.exists(item["cover_local"]):
        try:
            with open(item["cover_local"], "rb") as src, \
                 open(dest_album / "cover.jpg", "wb") as dst:
                dst.write(src.read())
        except Exception as e:
            log.warning("copy cover failed: %s", e)

    # Drop the spectrogram alongside the album as proof-of-lossless. Soulseek
    # convention is `spectrogram.png` or `spec.png`.
    if item.get("spectrogram_local") and os.path.exists(item["spectrogram_local"]):
        try:
            with open(item["spectrogram_local"], "rb") as src, \
                 open(dest_album / "spectrogram.png", "wb") as dst:
                dst.write(src.read())
        except Exception as e:
            log.warning("copy spectrogram failed: %s", e)

    # Drop artist.jpg in the ARTIST folder (parent of album), but only if
    # we don't already have one (don't overwrite a manually-curated photo).
    artist_jpg = Path(target_root) / artist_dir / "artist.jpg"
    if (item.get("artist_photo_local")
            and os.path.exists(item["artist_photo_local"])
            and not artist_jpg.exists()):
        try:
            artist_jpg.parent.mkdir(parents=True, exist_ok=True)
            with open(item["artist_photo_local"], "rb") as src, \
                 open(artist_jpg, "wb") as dst:
                dst.write(src.read())
        except Exception as e:
            log.warning("copy artist photo failed: %s", e)

    # Multi-disc detection: if any track has disc_no > 1, prefix track filename
    # with the disc number (D-NN, e.g. "1-01 - Track.flac").
    max_disc = max((int(t.get("disc_no") or 1) for t in tracks), default=1)
    multi_disc = max_disc > 1

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
                # For compilations: keep track artist intact, set albumartist
                # to "Various Artists" so Navidrome groups under VA.
                if not is_va:
                    audio.tags["artist"] = item["artist"] or ""
                audio.tags["albumartist"] = album_artist
                audio.tags["album"]       = item["title"] or ""
                audio.tags["title"]       = t["title"]    or src.stem
                if item["year"]:
                    audio.tags["date"] = str(item["year"])
                if item["genre"]:
                    audio.tags["genre"] = item["genre"]
                if t.get("track_no"):
                    audio.tags["tracknumber"] = str(t["track_no"])
                if t.get("disc_no"):
                    audio.tags["discnumber"] = str(t["disc_no"])
                if mb_release_id:
                    audio.tags["musicbrainz_albumid"] = mb_release_id
                if is_va:
                    audio.tags["compilation"] = "1"
                # Embed plain lyrics in standard tag (synced go in .lrc next door)
                if t.get("lyrics_plain"):
                    audio.tags["lyrics"] = t["lyrics_plain"]
                audio.save()
                # Embed the cover art (sidecar cover.jpg is still written too)
                _embed_cover(audio, item.get("cover_local"))
        except Exception as e:
            log.warning("tag write failed %s: %s", src, e)

        # Build target filename
        tn = "{:02d}".format(t["track_no"]) if t.get("track_no") else "00"
        if multi_disc:
            tn = "{}-{}".format(t.get("disc_no") or 1, tn)
        title = _safe_path(t["title"] or src.stem)
        dest = dest_album / f"{tn} - {title}{src.suffix.lower()}"
        try:
            if KEEP_SOURCE:
                shutil.copy2(src, dest)
            else:
                src.replace(dest)
        except Exception as e:
            log.error("place failed %s -> %s: %s", src, dest, e)
            continue

        # Write synced lyrics (.lrc) alongside the audio file
        if t.get("lyrics_synced"):
            lrc_dest = dest.with_suffix(".lrc")
            try:
                lrc_dest.write_text(t["lyrics_synced"], encoding="utf-8")
            except Exception as e:
                log.warning("lrc write failed %s: %s", lrc_dest, e)

    # Cross-album ReplayGain - one-shot rsgain over the new folder.
    _run_replaygain(dest_album)

    # Clean up the (now-empty) source folder so the inbox stays tidy. Only
    # when we actually moved (not copied). After deleting the source dir,
    # walk UP the parent chain - if slskd preserved an artist folder above
    # the album, we want that gone too once it's empty. Stop at the
    # configured downloads root to never delete it.
    if not KEEP_SOURCE:
        try:
            src_root = Path(item["source_path"])
            downloads_root = Path(os.environ.get(
                "REFINERY_DOWNLOADS",
                "/mnt/storage/downloads/slskd/complete",
            )).resolve()
            if src_root.is_dir():
                JUNK_EXTS = {".nfo", ".m3u", ".m3u8", ".cue", ".sfv",
                             ".log", ".txt", ".jpg", ".jpeg", ".png", ".pdf"}
                for f in src_root.rglob("*"):
                    if f.is_file() and (f.name.startswith(".")
                                        or f.suffix.lower() in JUNK_EXTS):
                        try: f.unlink()
                        except Exception: pass
                # Remove empty subdirs bottom-up
                for d in sorted([p for p in src_root.rglob("*") if p.is_dir()],
                                key=lambda p: -len(p.parts)):
                    try: d.rmdir()
                    except OSError: pass
                # Drop the root itself if empty
                try: src_root.rmdir()
                except OSError as e:
                    log.info("source not empty, leaving in place: %s (%s)",
                             src_root, e)
                # Walk up parents while empty, never above downloads_root
                current = src_root.parent
                while (current.exists()
                       and current.resolve() != downloads_root
                       and downloads_root in current.resolve().parents):
                    try:
                        current.rmdir()
                    except OSError:
                        break
                    current = current.parent
        except Exception as e:
            log.warning("source cleanup failed: %s", e)

    return str(dest_album)
