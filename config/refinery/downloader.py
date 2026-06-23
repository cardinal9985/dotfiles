"""URL downloader using yt-dlp. Accepts bandcamp / youtube / soundcloud /
anything yt-dlp supports, drops audio into the inbox so the scanner picks
it up like any other download."""

import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

log = logging.getLogger("refinery.downloader")

DOWNLOADS_DIR = os.environ.get("REFINERY_DOWNLOADS",
                                "/mnt/storage/downloads/slskd/complete")


def download(url):
    """Run yt-dlp into a hidden temp folder, then promote each resulting
    album folder into the inbox root so the scanner sees it as a new entry.
    Returns the list of promoted folder paths."""
    ts  = time.strftime("%Y%m%d-%H%M%S")
    tmp = Path(DOWNLOADS_DIR) / f".dl-{ts}-{uuid.uuid4().hex[:6]}"
    tmp.mkdir(parents=True, exist_ok=True)

    # Output template builds <album-or-playlist-or-title>/<NN - track>.<ext>
    # Comma syntax = field fallback: first non-empty wins.
    # The leading dot on the parent dir hides it from the scanner mid-download.
    out_tmpl = str(
        tmp
        / "%(album,playlist_title,title|Unknown Album)s"
        / "%(track_number,playlist_index|1)s - %(track,title|track)s.%(ext)s"
    )

    cmd = [
        "yt-dlp",
        "-f", "bestaudio/best",
        "-x",
        "--audio-format",  "mp3",
        "--audio-quality", "0",         # 0 = best (V0 for VBR, 320k for CBR)
        "--embed-metadata",
        "--embed-thumbnail",
        "--no-progress",
        "--no-warnings",
        "-o", out_tmpl,
        url,
    ]
    log.info("yt-dlp: %s -> %s", url, tmp)

    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            tail = "\n".join((p.stderr or "").splitlines()[-15:])
            raise RuntimeError(f"yt-dlp exit {p.returncode}: {tail}")
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    promoted = []
    for album in tmp.iterdir():
        if not album.is_dir():
            continue
        dest = Path(DOWNLOADS_DIR) / album.name
        if dest.exists():
            dest = Path(DOWNLOADS_DIR) / f"{album.name} ({ts})"
        shutil.move(str(album), str(dest))
        log.info("promoted %s -> %s", album, dest)
        promoted.append(str(dest))

    shutil.rmtree(tmp, ignore_errors=True)
    return promoted
