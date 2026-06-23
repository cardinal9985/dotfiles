import json
import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from flask import (Flask, render_template, request, redirect, url_for, abort,
                   send_file)

import db
import genres
import music
import scanner

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("refinery")

app = Flask(__name__)
db.init_db()

MUSIC_TARGET = os.environ.get("REFINERY_MUSIC_TARGET",
                              "/mnt/storage/media/music")

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
    with db.get_db() as conn:
        ready = conn.execute(
            "SELECT * FROM items WHERE status = 'ready' "
            "ORDER BY processed_at DESC"
        ).fetchall()
        recent = conn.execute(
            "SELECT * FROM items WHERE status IN ('approved', 'rejected', 'failed') "
            "ORDER BY decided_at DESC, processed_at DESC LIMIT 20"
        ).fetchall()
    return render_template("queue.html", user=user, ready=ready, recent=recent)


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
    return render_template("edit.html", user=user, item=item, tracks=tracks,
                           meta=meta, genres=genres.ALL)


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
            conn.execute(
                "UPDATE tracks SET title=?, track_no=?, disc_no=? WHERE id=?",
                (td["title"], td["track_no"], td["disc_no"], td["id"]),
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


@app.route("/_scan", methods=["POST"])
def scan_now():
    user = _get_user()
    if not user:
        return "unauthorized", 401
    scanner.scan_once()
    return redirect(url_for("queue"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006)
