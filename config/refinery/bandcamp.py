"""Bandcamp free-download client. Drives the freeDownloadPage flow to fetch
the real FLAC/MP3-320 zip for name-your-price ($0+) releases, instead of
ripping the 128k stream like yt-dlp does.

Fragile by design: Bandcamp tweaks the form internals occasionally. When it
breaks, fix the data-attribute names and the download_items shape here."""

import html as _html
import json
import logging
import os
import re
import shutil
import time
import urllib.parse
import zipfile
from pathlib import Path

import requests

log = logging.getLogger("refinery.bandcamp")

UA = ("Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
      "Gecko/20100101 Firefox/128.0")

DOWNLOADS_DIR = os.environ.get("REFINERY_DOWNLOADS",
                                "/mnt/storage/downloads/slskd/complete")

# Try these in order; first one Bandcamp offers wins.
FORMAT_PRIORITY = ["flac", "mp3-320", "mp3-v0", "aac-hi", "ogg-vorbis", "mp3-128"]


def is_bandcamp(url):
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host == "bandcamp.com" or host.endswith(".bandcamp.com")


def _parse_data_attr(html_text, attr):
    """Extract a JSON value from data-<attr>='...' attribute."""
    for q in ('"', "'"):
        m = re.search(rf'data-{re.escape(attr)}={q}([^{q}]+){q}', html_text)
        if m:
            return json.loads(_html.unescape(m.group(1)))
    return None


def _stat_then_fetch(s, zip_url, dest_path):
    """Bandcamp's download URL sometimes 302s straight to the zip, sometimes
    needs a 'stat' poll first while the server encodes the format. We just
    follow redirects and stream; if it returns JSON instead of bytes, we
    parse and retry the real URL."""
    for attempt in range(30):
        with s.get(zip_url, stream=True, timeout=600,
                   allow_redirects=True) as r:
            r.raise_for_status()
            ct = r.headers.get("Content-Type", "")
            if "json" in ct.lower():
                payload = r.json()
                # On older flow this returns {"download_url": "..."} or
                # {"result": "ok", "url": "..."}
                next_url = (payload.get("download_url")
                            or payload.get("url"))
                if not next_url:
                    raise RuntimeError(f"stat poll returned no URL: {payload}")
                zip_url = next_url
                time.sleep(2)
                continue
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(1024 * 64):
                    f.write(chunk)
            return
    raise RuntimeError("gave up waiting for Bandcamp to encode the zip")


def download(url, format_priority=None):
    """Download a free/name-your-price Bandcamp release as a real format
    zip. Raises if the release isn't free or if the page shape is unfamiliar."""
    fmts = format_priority or FORMAT_PRIORITY

    s = requests.Session()
    s.headers["User-Agent"] = UA

    log.info("bandcamp: GET album page %s", url)
    r = s.get(url, timeout=30)
    r.raise_for_status()

    tralbum = _parse_data_attr(r.text, "tralbum")
    if not tralbum:
        raise RuntimeError("could not find data-tralbum on album page")

    artist = (tralbum.get("artist")
              or (tralbum.get("current") or {}).get("band_name")
              or "Unknown Artist")
    album  = ((tralbum.get("current") or {}).get("title")
              or tralbum.get("album_title")
              or "Unknown Album")

    free_url = tralbum.get("freeDownloadPage")
    if not free_url:
        raise RuntimeError(
            f"'{artist} - {album}' is not free / name-your-price. Buy it on "
            "Bandcamp and drop the zip into the UPLOAD form for FLAC."
        )

    log.info("bandcamp: free download page %s", free_url)
    fr = s.get(free_url, timeout=30)
    fr.raise_for_status()
    blob = _parse_data_attr(fr.text, "blob")
    if not blob:
        raise RuntimeError(
            "free-download page has no data-blob - likely needs email "
            "verification (not supported by refinery)"
        )

    items = blob.get("download_items") or []
    if not items:
        raise RuntimeError("free-download blob has no download_items")

    ts  = time.strftime("%Y%m%d-%H%M%S")
    tmp = Path(DOWNLOADS_DIR) / f".bcdl-{ts}"
    tmp.mkdir(parents=True, exist_ok=True)

    promoted = []
    try:
        for item in items:
            downloads = item.get("downloads") or {}
            picked = None
            for fmt in fmts:
                d = downloads.get(fmt)
                if d and d.get("url"):
                    picked = (fmt, d["url"])
                    break
            if not picked:
                raise RuntimeError(
                    f"none of {fmts} available; offered: {sorted(downloads)}"
                )

            fmt, zip_url = picked
            log.info("bandcamp: '%s - %s' as %s", artist, album, fmt)

            zip_path = tmp / "_dl.zip"
            _stat_then_fetch(s, zip_url, zip_path)

            album_safe = re.sub(r'[<>:"|?*\\/]', "_", album).strip() or "Album"
            inner = tmp / album_safe
            inner.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(inner)
            os.remove(zip_path)

            final = Path(DOWNLOADS_DIR) / album_safe
            if final.exists():
                final = Path(DOWNLOADS_DIR) / f"{album_safe} ({ts})"
            shutil.move(str(inner), str(final))
            promoted.append(str(final))
            log.info("bandcamp: promoted -> %s", final)

        return promoted
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
