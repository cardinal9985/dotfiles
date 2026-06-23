"""Watch the downloads folder. For each new top-level entry, classify by
content extension and dispatch to the right processor."""

import logging
import os
import time
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import db
import book
import music

WORKERS = int(os.environ.get("REFINERY_WORKERS", "3"))

log = logging.getLogger("refinery.scanner")

DOWNLOADS_DIR = os.environ.get("REFINERY_DOWNLOADS",
                                "/mnt/storage/downloads")
# 0 = no wait. slskd already separates in-progress (incomplete/) from done
# (complete/), so anything we see is finished. Raise via env if a future
# source writes directly without atomic moves (e.g. mergerfs cross-disk).
STABILITY_SECS = int(os.environ.get("REFINERY_STABILITY_SECS", "0"))

MUSIC_EXTS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wma", ".wav",
              ".alac", ".aiff", ".aif"}
VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v"}
BOOK_EXTS  = {".epub", ".pdf", ".mobi", ".azw", ".azw3", ".cbz", ".cbr"}
GAME_EXTS  = {".nes", ".smc", ".sfc", ".gba", ".gb", ".gbc", ".n64", ".z64",
              ".iso", ".bin", ".chd", ".cue", ".md", ".smd", ".a26"}


def classify_folder(path):
    counts = Counter()
    p = Path(path)
    if p.is_file():
        ext = p.suffix.lower()
    else:
        for f in p.rglob("*"):
            if f.is_file():
                counts[f.suffix.lower()] += 1

    music_count = sum(c for ext, c in counts.items() if ext in MUSIC_EXTS)
    video_count = sum(c for ext, c in counts.items() if ext in VIDEO_EXTS)
    book_count  = sum(c for ext, c in counts.items() if ext in BOOK_EXTS)
    game_count  = sum(c for ext, c in counts.items() if ext in GAME_EXTS)

    scored = {"music": music_count, "video": video_count,
              "book":  book_count,  "game":  game_count}
    winner = max(scored, key=scored.get)
    return winner if scored[winner] > 0 else None


def is_stable(path):
    """Return True if no file in `path` has been modified in STABILITY_SECS."""
    if STABILITY_SECS <= 0:
        return True
    cutoff = time.time() - STABILITY_SECS
    p = Path(path)
    if p.is_file():
        return p.stat().st_mtime < cutoff
    for f in p.rglob("*"):
        if f.is_file() and f.stat().st_mtime > cutoff:
            return False
    return True


def maybe_extract_zip(path):
    """If path is a single .zip file, extract it to a sibling folder and
    return the new folder path. Otherwise return original path."""
    p = Path(path)
    if p.is_file() and p.suffix.lower() == ".zip":
        out_dir = p.with_suffix("")
        out_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(p, "r") as zf:
                zf.extractall(out_dir)
            log.info("extracted %s -> %s", p, out_dir)
            return str(out_dir)
        except Exception as e:
            log.warning("zip extract failed %s: %s", p, e)
    return str(p)


def already_seen(source_path):
    with db.get_db() as conn:
        row = conn.execute("SELECT 1 FROM items WHERE source_path = ?",
                           (source_path,)).fetchone()
    return row is not None


def _existing_status(source_path):
    with db.get_db() as conn:
        row = conn.execute("SELECT status FROM items WHERE source_path = ?",
                           (source_path,)).fetchone()
    return row["status"] if row else None


def _process_one(full):
    """Worker entry point: classify and dispatch a single download entry."""
    kind = None
    try:
        work = maybe_extract_zip(full)
        kind = classify_folder(work)
        if not kind:
            log.warning("could not classify %s", work)
            return
        log.info("New %s detected: %s", kind, work)
        # Mark as processing so the UI can show in-flight items.
        with db.get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO items
                     (media_type, status, source_path, processed_at)
                   VALUES (?, 'processing', ?, datetime('now'))""",
                (kind, work),
            )
        if kind == "music":
            music.process_album(work)
        elif kind == "book":
            book.process_book(work)
        else:
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE items SET status='failed', error=? WHERE source_path=?",
                    (f"{kind} processor not implemented yet", work),
                )
    except Exception as e:
        log.exception("processing failed for %s", full)
        with db.get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO items
                     (media_type, status, source_path, error, processed_at)
                   VALUES (?, 'failed', ?, ?, datetime('now'))""",
                (kind or "unknown", full, str(e)[:500]),
            )


def scan_once(force=False):
    if not os.path.isdir(DOWNLOADS_DIR):
        log.warning("downloads dir missing: %s", DOWNLOADS_DIR)
        return
    todo = []
    for entry in sorted(os.listdir(DOWNLOADS_DIR)):
        if entry.startswith("_") or entry.startswith("."):
            continue
        full = os.path.join(DOWNLOADS_DIR, entry)
        status = _existing_status(full)
        if status:
            # Already in DB. Forced manual scans should still refresh items
            # that haven't been acted on yet - this is how a partially-downloaded
            # album that finished later gets its full track list. We never
            # re-touch approved items (would clobber the library copy).
            if force and status in ("ready", "processing", "failed"):
                with db.get_db() as conn:
                    conn.execute("DELETE FROM items WHERE source_path = ?", (full,))
                log.info("forced re-scan: dropped existing %s row for %s",
                         status, full)
            else:
                continue
        if not force and not is_stable(full):
            log.debug("not stable yet: %s", full)
            continue
        todo.append(full)
    if not todo:
        return
    log.info("dispatching %d item(s) to %d worker(s)", len(todo), WORKERS)
    with ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="refinery-worker") as ex:
        for full in todo:
            ex.submit(_process_one, full)
