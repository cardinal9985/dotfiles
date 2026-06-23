import json
import logging
import os
import shutil
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from flask import (Flask, render_template, request, redirect, url_for, abort,
                   send_file)

import db
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
db.init_db()

MUSIC_TARGET = os.environ.get("REFINERY_MUSIC_TARGET",
                              "/mnt/storage/media/music")


# Reset any items left in 'processing' state from a previous crash so they
# don't sit invisibly forever.
with db.get_db() as _conn:
    _conn.execute(
        "UPDATE items SET status='failed', error='interrupted - service restart' "
        "WHERE status='processing'"
    )

sched = BackgroundScheduler(job_defaults={"max_instances": 1, "coalesce": True})
sched.add_job(scanner.scan_once, "interval", minutes=1, id="scan",
              next_run_time=datetime.now() + timedelta(seconds=15))
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
            "ORDER BY decided_at DESC, processed_at DESC LIMIT 20"
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
    # Conflict check: is there already a folder where we'd write this?
    conflict = None
    if item["media_type"] == "music":
        target = music.library_path_for(MUSIC_TARGET, item["artist"],
                                        item["year"], item["title"])
        if target.exists():
            conflict = str(target)
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

        # Update each track from form
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
    if item_dict["media_type"] == "music":
        try:
            dest = music.write_and_move(item_dict, tracks, MUSIC_TARGET)
            log.info("Approved music album %d → %s", item_id, dest)
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
    if item["media_type"] == "music":
        music.process_album(item["source_path"])
    return redirect(url_for("queue"))


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
    user = _get_user()
    artists = library.list_artists()
    return render_template("library.html", user=user, artists=artists)


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
    music.process_album(folder)
    return redirect(url_for("queue"))


@app.route("/_scan", methods=["POST"])
def scan_now():
    """Manual scan from the SCAN NOW button - bypass the stability check so
    the user can process a download immediately without waiting for the timer."""
    user = _get_user()
    if not user:
        return "unauthorized", 401
    scanner.scan_once(force=True)
    return redirect(url_for("queue"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006)
