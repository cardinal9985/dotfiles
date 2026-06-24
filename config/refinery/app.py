import json
import logging
import os
import shutil
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from flask import (Flask, render_template, request, redirect, url_for, abort,
                   send_file)

import book
import db
import downloader
import genres
import library
import music
import scanner

NTFY_URL   = os.environ.get("NTFY_URL", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_TOKEN = os.environ.get("NTFY_TOKEN", "")


def notify(title, message):
    """Best-effort ntfy push. Silently swallows failures."""
    if not (NTFY_URL and NTFY_TOPIC):
        return
    try:
        req = urllib.request.Request(
            f"{NTFY_URL.rstrip('/')}/{NTFY_TOPIC}",
            data=message.encode(),
            headers={
                "Title": title,
                "Tags":  "card_file_box",
                **({"Authorization": "Bearer " + NTFY_TOKEN} if NTFY_TOKEN else {}),
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


# Patch music.process_album to notify when an item lands in the queue.
_orig_process_album = music.process_album
def _process_album_with_notify(folder):
    item_id = _orig_process_album(folder)
    if item_id:
        with db.get_db() as conn:
            row = conn.execute("SELECT title, artist FROM items WHERE id=?",
                               (item_id,)).fetchone()
        if row:
            notify("Refinery: ready for review",
                   f"{row['artist'] or '?'} - {row['title'] or '?'}")
    return item_id
music.process_album = _process_album_with_notify

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("refinery")

app = Flask(__name__)
# Trusted single-user instance - allow large uploads (4K movies, multi-disc
# ROMs, audiobook bundles). Werkzeug streams multipart uploads to disk via
# tempfiles so this doesn't load the whole thing in memory. For uploads in
# the multi-GB range, SCP/rsync over SSH is more reliable than browser
# upload, but this option exists for one-off convenience.
app.config["MAX_CONTENT_LENGTH"] = None
db.init_db()

MUSIC_TARGET = os.environ.get("REFINERY_MUSIC_TARGET",
                              "/mnt/storage/media/music")
BOOK_TARGET  = os.environ.get("REFINERY_BOOK_TARGET",
                              "/mnt/storage/media/books")


# Reset any items left in 'processing' state from a previous crash so they
# don't sit invisibly forever. decided_at is what RECENT DECISIONS sorts on,
# so without it these rows fall past LIMIT 20 and look like they vanished.
with db.get_db() as _conn:
    _conn.execute(
        "UPDATE items SET status='failed', "
        "error='interrupted - service restart', "
        "decided_at=datetime('now') "
        "WHERE status='processing'"
    )

def _radar_prewarm():
    """Walk every library artist so the discography cache is warm.
    Runs on a daily timer; rate limiting (1 req/s to MB) makes the first
    pass slow but subsequent ones touch only stale entries."""
    try:
        for a in library.list_artists():
            library.discography(a["name"])
    except Exception:
        log.exception("radar prewarm failed")


def _book_radar_prewarm():
    """Same for the books library against OpenLibrary - keeps the book
    radar instant once seeded."""
    try:
        for a in library.list_authors():
            library.book_works(a["name"])
    except Exception:
        log.exception("book radar prewarm failed")


sched = BackgroundScheduler(job_defaults={"max_instances": 1, "coalesce": True})
sched.add_job(scanner.scan_once, "interval", minutes=1, id="scan",
              next_run_time=datetime.now() + timedelta(seconds=15))
sched.add_job(_radar_prewarm, "interval", hours=24, id="radar_prewarm",
              next_run_time=datetime.now() + timedelta(minutes=5))
sched.add_job(_book_radar_prewarm, "interval", hours=24, id="book_radar_prewarm",
              next_run_time=datetime.now() + timedelta(minutes=10))
sched.start()


def _get_user():
    return request.headers.get("Remote-User", "").lower()


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return "ok", 200


@app.route("/")
def queue():
    user = _get_user()
    q = request.args.get("q", "").strip().lower()
    with db.get_db() as conn:
        ready = conn.execute(
            "SELECT * FROM items WHERE status = 'ready' "
            "ORDER BY processed_at DESC"
        ).fetchall()
        processing = conn.execute(
            "SELECT * FROM items WHERE status = 'processing' "
            "ORDER BY processed_at DESC"
        ).fetchall()
        recent = conn.execute(
            "SELECT * FROM items WHERE status IN ('approved', 'rejected', 'failed') "
            "ORDER BY COALESCE(decided_at, processed_at) DESC LIMIT 20"
        ).fetchall()
    if q:
        def _match(r):
            return any(q in (r[c] or "").lower()
                       for c in ("title", "artist", "source_path"))
        ready      = [r for r in ready      if _match(r)]
        processing = [r for r in processing if _match(r)]
        recent     = [r for r in recent     if _match(r)]
    return render_template("queue.html", user=user, ready=ready,
                           processing=processing, recent=recent, q=q)


@app.route("/item/<int:item_id>")
def edit(item_id):
    user = _get_user()
    with db.get_db() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?",
                            (item_id,)).fetchone()
        if not item:
            abort(404)
        tracks = conn.execute(
            "SELECT * FROM tracks WHERE item_id = ? ORDER BY disc_no, track_no",
            (item_id,)
        ).fetchall()
    meta = json.loads(item["meta_json"] or "{}")
    conflict = None
    if item["media_type"] == "music":
        target = music.library_path_for(MUSIC_TARGET, item["artist"],
                                        item["year"], item["title"])
        if target.exists():
            conflict = str(target)
        return render_template("edit.html", user=user, item=item, tracks=tracks,
                               meta=meta, genres=genres.ALL, conflict=conflict)
    if item["media_type"] == "book":
        target = book.library_path_for(BOOK_TARGET, item["artist"],
                                       item["title"], item["year"])
        if target.exists():
            conflict = str(target)
        return render_template("edit_book.html", user=user, item=item,
                               meta=meta, genres=genres.BOOKS, conflict=conflict)
    return render_template("edit.html", user=user, item=item, tracks=tracks,
                           meta=meta, genres=genres.ALL, conflict=conflict)


@app.route("/item/<int:item_id>/approve", methods=["POST"])
def approve(item_id):
    user = _get_user()
    if not user:
        return "unauthorized", 401

    with db.get_db() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?",
                            (item_id,)).fetchone()
        if not item:
            abort(404)

        # Pull edited fields from form
        title  = request.form.get("title", "").strip()
        artist = request.form.get("artist", "").strip()
        year   = request.form.get("year", "").strip()
        genre  = request.form.get("genre", "").strip()

        item_dict = dict(item)
        item_dict["title"]  = title  or item_dict["title"]
        item_dict["artist"] = artist or item_dict["artist"]
        item_dict["year"]   = int(year) if year.isdigit() else item_dict["year"]
        item_dict["genre"]  = genre  or item_dict["genre"]

        # Manual cover upload override
        cover_file = request.files.get("cover_upload")
        if cover_file and cover_file.filename:
            cover_dir = os.environ.get("REFINERY_COVER_DIR",
                                       "/persist/refinery/covers")
            os.makedirs(cover_dir, exist_ok=True)
            ext = os.path.splitext(cover_file.filename)[1].lower() or ".jpg"
            cover_path = os.path.join(cover_dir, f"manual_{item_id}{ext}")
            cover_file.save(cover_path)
            item_dict["cover_local"] = cover_path
            conn.execute("UPDATE items SET cover_local=? WHERE id=?",
                         (cover_path, item_id))

        # Books are single-file items; no tracks table to update
        if item_dict["media_type"] == "book":
            tracks_rows = []
        else:
            tracks_rows = conn.execute(
                "SELECT * FROM tracks WHERE item_id = ? ORDER BY disc_no, track_no",
                (item_id,)
            ).fetchall()
        tracks = []
        for t in tracks_rows:
            tid = t["id"]
            new_title = request.form.get(f"track_title_{tid}", "").strip()
            new_no    = request.form.get(f"track_no_{tid}", "").strip()
            new_disc  = request.form.get(f"track_disc_{tid}", "").strip()
            td = dict(t)
            td["title"]    = new_title or td["title"]
            td["track_no"] = int(new_no)   if new_no.isdigit()   else td["track_no"]
            td["disc_no"]  = int(new_disc) if new_disc.isdigit() else td["disc_no"]
            tracks.append(td)

        # Persist edits
        conn.execute(
            """UPDATE items SET title=?, artist=?, year=?, genre=? WHERE id=?""",
            (item_dict["title"], item_dict["artist"], item_dict["year"],
             item_dict["genre"], item_id),
        )
        for td in tracks:
            # Manual lyrics overrides per track. If the user uploaded a .lrc
            # or pasted into the textareas, persist those before approve.
            tid = td["id"]
            new_plain  = request.form.get(f"lyrics_plain_{tid}", None)
            new_synced = request.form.get(f"lyrics_synced_{tid}", None)
            lrc_file = request.files.get(f"lrc_upload_{tid}")
            if lrc_file and lrc_file.filename:
                try:
                    new_synced = lrc_file.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
            if new_plain is not None:
                td["lyrics_plain"] = new_plain.strip()
            if new_synced is not None:
                td["lyrics_synced"] = new_synced.strip()
            conn.execute(
                "UPDATE tracks SET title=?, track_no=?, disc_no=?, "
                "  lyrics_plain=?, lyrics_synced=? WHERE id=?",
                (td["title"], td["track_no"], td["disc_no"],
                 td.get("lyrics_plain"), td.get("lyrics_synced"),
                 td["id"]),
            )

    # Do the actual write + move outside the DB transaction
    try:
        if item_dict["media_type"] == "music":
            dest = music.write_and_move(item_dict, tracks, MUSIC_TARGET)
        elif item_dict["media_type"] == "book":
            convert_pdf = request.form.get("convert_pdf") == "1"
            dest = book.write_and_move(item_dict, BOOK_TARGET,
                                       convert_pdf=convert_pdf)
        else:
            raise ValueError(f"unknown media_type {item_dict['media_type']}")
        log.info("Approved %s %d → %s", item_dict["media_type"], item_id, dest)
    except Exception as e:
        log.exception("approve write failed")
        with db.get_db() as conn:
            conn.execute(
                "UPDATE items SET status='failed', error=?, decided_at=datetime('now') WHERE id=?",
                (str(e)[:500], item_id),
            )
        return redirect(url_for("queue"))

    with db.get_db() as conn:
        conn.execute(
            "UPDATE items SET status='approved', decided_at=datetime('now') WHERE id=?",
            (item_id,),
        )
    return redirect(url_for("queue"))


def _bg_process(media_type, source_path):
    """Process one item in a background thread so the HTTP response is
    instant. The user watches progress via the IN PROGRESS section."""
    try:
        if media_type == "music":
            music.process_album(source_path)
        elif media_type == "book":
            # Books: source_path is the actual file (one item per file)
            if os.path.isfile(source_path):
                book.process_book_file(source_path)
            elif os.path.isdir(source_path):
                book.process_book(source_path)
    except Exception:
        log.exception("bg processing failed for %s", source_path)


@app.route("/_retry_failed", methods=["POST"])
def retry_failed():
    """Bulk re-run the processor on every failed/rejected item whose source
    still exists. Spawns a background thread per item so the response is
    instant - items show up in IN PROGRESS as workers chew through them."""
    user = _get_user()
    if not user:
        return "unauthorized", 401

    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT id, source_path, media_type FROM items "
            "WHERE status IN ('failed', 'rejected')"
        ).fetchall()

    requeued = 0
    skipped  = 0
    for r in rows:
        src = r["source_path"]
        if not src or not (os.path.isdir(src) or os.path.isfile(src)):
            skipped += 1
            continue
        with db.get_db() as conn:
            conn.execute("DELETE FROM items WHERE id=?", (r["id"],))
        threading.Thread(
            target=_bg_process,
            args=(r["media_type"], src),
            daemon=True,
        ).start()
        requeued += 1

    notify("Refinery: retry failed",
           f"Re-queued {requeued}, skipped {skipped} (source gone)")
    return redirect(url_for("queue"))


@app.route("/_approve_verified", methods=["POST"])
def approve_verified():
    """Bulk-approve every ready item where ALL tracks are VERIFIED and no
    track is CORRUPT. Skips anything with SUSPECT/BORDERLINE/UNKNOWN."""
    user = _get_user()
    if not user:
        return "unauthorized", 401

    with db.get_db() as conn:
        candidates = conn.execute(
            "SELECT id FROM items WHERE status = 'ready'"
        ).fetchall()

    approved = 0
    for c in candidates:
        with db.get_db() as conn:
            tr = conn.execute(
                "SELECT quality_ok, quality_verdict FROM tracks WHERE item_id=?",
                (c["id"],),
            ).fetchall()
        if not tr:
            continue
        if any((t["quality_ok"] == 0)
               or (t["quality_verdict"] != "verified")
               for t in tr):
            continue
        # Reuse single-item approve path
        with app.test_request_context(f"/item/{c['id']}/approve",
                                       method="POST",
                                       headers={"Remote-User": user}):
            try:
                approve(c["id"])
                approved += 1
            except Exception as e:
                log.exception("bulk approve failed for %d: %s", c["id"], e)

    notify("Refinery: bulk approve",
           f"Approved {approved} of {len(candidates)} verified albums")
    return redirect(url_for("queue"))


@app.route("/item/<int:item_id>/reject", methods=["POST"])
def reject(item_id):
    user = _get_user()
    if not user:
        return "unauthorized", 401
    with db.get_db() as conn:
        conn.execute(
            "UPDATE items SET status='rejected', decided_at=datetime('now') WHERE id=?",
            (item_id,),
        )
    return redirect(url_for("queue"))


@app.route("/item/<int:item_id>/reanalyze", methods=["POST"])
def reanalyze(item_id):
    """Re-run quality + lyrics analysis on an existing item's tracks. Useful
    when columns were added later or when LRCLib failed first time around.
    Doesn't redo MB/Bandcamp lookups - use /reprocess for that."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    import quality
    with db.get_db() as conn:
        item = conn.execute("SELECT * FROM items WHERE id=?",
                            (item_id,)).fetchone()
        if not item:
            abort(404)
        tracks = conn.execute(
            "SELECT id, source_path, title, duration_secs FROM tracks WHERE item_id=?",
            (item_id,),
        ).fetchall()
    for t in tracks:
        q   = quality.analyze(t["source_path"])
        lyr = music.lrclib_get(item["artist"], t["title"],
                               item["title"], t["duration_secs"]) or {}
        with db.get_db() as conn:
            conn.execute("""
                UPDATE tracks SET
                  quality_ok      = ?,
                  quality_cutoff  = ?,
                  quality_verdict = ?,
                  quality_error   = ?,
                  lyrics_synced   = ?,
                  lyrics_plain    = ?
                WHERE id = ?
            """, (1 if q["verified"] else 0, q["freq_cutoff_hz"],
                  q["verdict"], q.get("error"),
                  lyr.get("synced") or "", lyr.get("plain") or "",
                  t["id"]))
    return redirect(url_for("edit", item_id=item_id))


@app.route("/item/<int:item_id>/forget", methods=["POST"])
def forget(item_id):
    """Tombstone the item so it disappears from the UI but the source path
    remains 'already seen' - otherwise the next scan would re-import the
    same files from disk."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    with db.get_db() as conn:
        conn.execute(
            "UPDATE items SET status='forgotten', decided_at=datetime('now') "
            "WHERE id=?", (item_id,)
        )
    return redirect(url_for("queue"))


@app.route("/item/<int:item_id>/reprocess", methods=["POST"])
def reprocess(item_id):
    """Re-run the processor for a failed/rejected item."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    with db.get_db() as conn:
        item = conn.execute("SELECT source_path, media_type FROM items WHERE id=?",
                            (item_id,)).fetchone()
        if not item:
            abort(404)
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    threading.Thread(
        target=_bg_process,
        args=(item["media_type"], item["source_path"]),
        daemon=True,
    ).start()
    return redirect(url_for("queue"))


@app.route("/item/<int:item_id>/cover.jpg")
def item_cover(item_id):
    if not _get_user():
        return "unauthorized", 401
    with db.get_db() as conn:
        row = conn.execute("SELECT cover_local FROM items WHERE id=?",
                           (item_id,)).fetchone()
    if not row or not row["cover_local"] or not os.path.exists(row["cover_local"]):
        abort(404)
    return send_file(row["cover_local"])


@app.route("/item/<int:item_id>/spectrogram.png")
def item_spectrogram(item_id):
    if not _get_user():
        return "unauthorized", 401
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT spectrogram_local FROM items WHERE id=?",
            (item_id,),
        ).fetchone()
    if not row or not row["spectrogram_local"] or not os.path.exists(row["spectrogram_local"]):
        abort(404)
    return send_file(row["spectrogram_local"], mimetype="image/png")


@app.route("/track/<int:track_id>/audio")
def track_audio(track_id):
    """Stream the source audio file for in-browser preview during approval.
    The path comes from the DB so we can't be tricked into serving arbitrary
    files. Range requests are handled by Flask's send_file."""
    if not _get_user():
        return "unauthorized", 401
    with db.get_db() as conn:
        row = conn.execute("SELECT source_path FROM tracks WHERE id=?",
                           (track_id,)).fetchone()
    if not row or not os.path.exists(row["source_path"]):
        abort(404)
    return send_file(row["source_path"], conditional=True)


@app.route("/library")
def library_index():
    user        = _get_user()
    artists     = library.list_artists()
    author_count = len(library.list_authors())
    return render_template("library.html", user=user, artists=artists,
                           author_count=author_count)


@app.route("/library/fix-missing-art", methods=["POST"])
def library_fix_missing_art():
    """One-shot: for every approved music item missing a spectrogram or
    cover, find the files in the music library (source_path stays pointing
    at the long-deleted download folder), regenerate the spectrogram with
    the new sox-trim defaults, and extract embedded cover art when none was
    found on first pass."""
    user = _get_user()
    if not user:
        return "unauthorized", 401

    def _run():
        import hashlib, quality
        with db.get_db() as conn:
            rows = conn.execute(
                """SELECT id, artist, year, title, cover_local,
                          spectrogram_local
                   FROM items
                   WHERE media_type='music' AND status='approved'
                     AND (spectrogram_local IS NULL OR spectrogram_local=''
                          OR cover_local IS NULL OR cover_local='')"""
            ).fetchall()
        log.info("fix-missing-art: %d candidate item(s)", len(rows))
        for r in rows:
            dest = music.library_path_for(MUSIC_TARGET, r["artist"],
                                          r["year"], r["title"])
            if not dest.exists():
                log.warning("fix-missing-art: %s not on disk, skipping", dest)
                continue
            audio_files = sorted(
                str(p) for p in dest.rglob("*")
                if p.is_file() and p.suffix.lower() in music.MUSIC_EXTS
            )
            if not audio_files:
                continue

            updates = {}

            if not r["spectrogram_local"]:
                # Pick the longest by file size (approximation - avoids
                # parsing each file just to get duration).
                longest = max(audio_files, key=os.path.getsize)
                key  = hashlib.sha1(str(dest).encode()).hexdigest()[:16]
                spec = os.path.join(music.SPECTROGRAM_DIR, f"{key}.png")
                if quality.generate_spectrogram(longest, spec):
                    updates["spectrogram_local"] = spec

            if not r["cover_local"]:
                cover = music.extract_embedded_cover(
                    audio_files, music.COVER_DIR)
                if cover:
                    updates["cover_local"] = cover

            if updates:
                cols = ", ".join(f"{k}=?" for k in updates)
                with db.get_db() as conn:
                    conn.execute(f"UPDATE items SET {cols} WHERE id=?",
                                 (*updates.values(), r["id"]))
                log.info("fix-missing-art: id=%d %s", r["id"],
                         ", ".join(updates))

    threading.Thread(target=_run, daemon=True,
                     name="refinery-fixart").start()
    return redirect(url_for("library_index"))


@app.route("/library/books")
def library_books():
    user    = _get_user()
    authors = library.list_authors()
    return render_template("library_books.html", user=user, authors=authors)


@app.route("/library/books/radar")
def library_books_radar():
    user = _get_user()
    try:
        days = max(1, min(int(request.args.get("days", 730)), 3650))
    except (TypeError, ValueError):
        days = 730
    releases = library.book_radar(days=days)
    return render_template("library_books_radar.html", user=user,
                           releases=releases, days=days)


@app.route("/library/books/<path:author>")
def library_books_author(author):
    user    = _get_user()
    books   = library.books_for(author)
    missing = library.missing_books(author)
    return render_template("library_books_author.html", user=user,
                           author=author, books=books, missing=missing)


@app.route("/library/books/<path:author>/<path:title>/cover")
def library_book_cover(author, title):
    """Serve cover.jpg / cover.png from a book folder. Path-traversal guard
    keeps requests inside BOOK_TARGET even with crafty %2F input."""
    book_root = Path(BOOK_TARGET).resolve()
    folder    = (book_root / author / title).resolve()
    if not str(folder).startswith(str(book_root) + os.sep):
        abort(403)
    for name in ("cover.jpg", "cover.jpeg", "cover.png"):
        p = folder / name
        if p.exists():
            return send_file(str(p))
    abort(404)


@app.route("/library/radar")
def library_radar():
    user = _get_user()
    try:
        days = max(1, min(int(request.args.get("days", 180)), 3650))
    except (TypeError, ValueError):
        days = 180
    upcoming = request.args.get("upcoming", "1") != "0"
    releases = library.radar(days=days, include_upcoming=upcoming)
    return render_template("library_radar.html", user=user,
                           releases=releases, days=days, upcoming=upcoming)


@app.route("/library/<path:artist>")
def library_artist(artist):
    user = _get_user()
    owned = library.albums_for(artist)
    missing = library.missing_albums(artist)
    return render_template("library_artist.html", user=user,
                           artist=artist, owned=owned, missing=missing)


def _safe_under_root(target_str, root_str):
    """Return resolved Path if `target_str` is strictly under `root_str`
    (and not equal to it). Otherwise None. Guards delete actions."""
    try:
        root   = Path(root_str).resolve()
        target = Path(target_str).resolve()
    except Exception:
        return None
    if target == root:
        return None
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def _cleanup_empty_parents(start, root):
    """Walk up from `start` (exclusive), rmdir-ing each parent that's now
    empty. Stops at `root` (won't delete the root itself)."""
    current = Path(start).parent
    root_resolved = Path(root).resolve()
    while current.resolve() != root_resolved and current.exists():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


@app.route("/library/delete-album", methods=["POST"])
def library_delete_album():
    """Recursively delete one album folder, then walk up to remove an
    artist folder that has no albums left."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    folder = request.form.get("folder", "")
    target = _safe_under_root(folder, MUSIC_TARGET)
    if not target or not target.is_dir():
        return "bad folder", 400
    artist_name = request.form.get("artist", "")
    try:
        shutil.rmtree(target)
        _cleanup_empty_parents(target, MUSIC_TARGET)
        notify("Refinery: deleted album", f"{artist_name} - {target.name}")
    except Exception as e:
        log.exception("delete-album failed for %s", target)
        return f"delete failed: {e}", 500
    if artist_name and (Path(MUSIC_TARGET) / artist_name).exists():
        return redirect(url_for("library_artist", artist=artist_name))
    return redirect(url_for("library_index"))


@app.route("/library/delete-artist", methods=["POST"])
def library_delete_artist():
    """Delete an entire artist folder (all their albums)."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    artist = (request.form.get("artist", "") or "").strip()
    if not artist:
        return "missing artist", 400
    candidate = str(Path(MUSIC_TARGET) / artist)
    target = _safe_under_root(candidate, MUSIC_TARGET)
    if not target or not target.is_dir():
        return "artist folder not found", 400
    try:
        shutil.rmtree(target)
        notify("Refinery: deleted artist", artist)
    except Exception as e:
        log.exception("delete-artist failed for %s", target)
        return f"delete failed: {e}", 500
    return redirect(url_for("library_index"))


@app.route("/library/reprocess", methods=["POST"])
def library_reprocess():
    """Send an existing library album back through the music processor.
    Re-runs tagging / cover / spectrogram / MB lookup and stages it in the
    approval queue. Approve will write back to the same artist/year-album
    location (may rename folder if normalized differently)."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    folder = request.form.get("folder", "")
    if not folder or not os.path.isdir(folder):
        return "bad folder", 400
    # Drop any prior queue row for this folder (re-process invalidates it)
    with db.get_db() as conn:
        conn.execute("DELETE FROM items WHERE source_path = ?", (folder,))
    threading.Thread(
        target=_bg_process, args=("music", folder), daemon=True,
    ).start()
    return redirect(url_for("queue"))


@app.route("/_download", methods=["POST"])
def download_url():
    """Pull a URL (bandcamp/youtube/soundcloud/etc) via yt-dlp into the
    inbox. Audio always lands as MP3 at the best quality the source offers.
    Runs in the background so the user gets the queue page back immediately."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    url = (request.form.get("url") or "").strip()
    if not url:
        return redirect(url_for("queue"))

    def _run():
        try:
            promoted = downloader.download(url)
            if promoted:
                notify("Refinery: download done",
                       f"{len(promoted)} folder(s) from {url} - scanning")
                # Kick a scan so the new folders get classified right away
                scanner.scan_once(force=True)
            else:
                notify("Refinery: download empty", url)
        except Exception as e:
            log.exception("download failed: %s", url)
            notify("Refinery: download FAILED", f"{url}\n{e}")

    threading.Thread(target=_run, daemon=True,
                     name="refinery-downloader").start()
    return redirect(url_for("queue"))


@app.route("/_upload", methods=["POST"])
def upload():
    """Manually upload one or more files into the slskd-complete inbox so
    refinery picks them up on the next scan. Files get grouped into a
    timestamped subfolder (or user-provided folder name)."""
    user = _get_user()
    if not user:
        return "unauthorized", 401

    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        return redirect(url_for("queue"))

    name = (request.form.get("folder") or "").strip()
    if not name:
        name = "upload-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    # Strip filesystem-hostile characters from folder name
    import re as _re
    name = _re.sub(r'[<>:"|?*\\\\/]', "", name)[:120] or "upload"

    dest = Path(scanner.DOWNLOADS_DIR) / name
    dest.mkdir(parents=True, exist_ok=True)

    saved = 0
    for f in files:
        # Use only the filename, never any path the client may have sent
        safe = os.path.basename(f.filename)
        if not safe:
            continue
        f.save(str(dest / safe))
        saved += 1

    notify("Refinery: manual upload",
           f"{saved} file(s) uploaded to {name}")
    # Background scan so the user gets the queue page immediately - the
    # actual processing (OpenLibrary lookups, cover downloads, etc.) can
    # take 10-30s per book and shouldn't block the upload response.
    threading.Thread(target=scanner.scan_once, args=(True,), daemon=True).start()
    return redirect(url_for("queue"))


@app.route("/_scan", methods=["POST"])
def scan_now():
    """Manual scan from the SCAN NOW button - bypass the stability check so
    the user can process a download immediately without waiting for the timer.
    Runs in a background thread so the response is instant."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    threading.Thread(target=scanner.scan_once, args=(True,), daemon=True).start()
    return redirect(url_for("queue"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006)
