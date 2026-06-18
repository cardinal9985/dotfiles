import json
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for

import db
from poller import poll_jellyfin, poll_navidrome, poll_romm, poll_booklore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("wrapped")

app = Flask(__name__)

db.init_db()

# ── Background Scheduler ─────────────────────────────────────────────────────

scheduler = BackgroundScheduler()
scheduler.add_job(poll_jellyfin, "interval", minutes=5, id="poll_jellyfin",
                  next_run_time=None)
scheduler.add_job(poll_navidrome, "interval", minutes=5, id="poll_navidrome",
                  next_run_time=None)
scheduler.add_job(poll_romm, "interval", minutes=15, id="poll_romm",
                  next_run_time=None)
scheduler.add_job(poll_booklore, "interval", minutes=5, id="poll_booklore",
                  next_run_time=None)
scheduler.start()

# Run initial poll after a short delay
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta

scheduler.add_job(poll_jellyfin, DateTrigger(
    run_date=datetime.now() + timedelta(seconds=10)), id="init_jellyfin")
scheduler.add_job(poll_navidrome, DateTrigger(
    run_date=datetime.now() + timedelta(seconds=15)), id="init_navidrome")
scheduler.add_job(poll_romm, DateTrigger(
    run_date=datetime.now() + timedelta(seconds=20)), id="init_romm")
scheduler.add_job(poll_booklore, DateTrigger(
    run_date=datetime.now() + timedelta(seconds=25)), id="init_booklore")


def _get_user():
    return request.headers.get("Remote-User", "").lower()


def _format_duration(secs):
    if not secs:
        return "0m"
    hours = secs // 3600
    minutes = (secs % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _parse_metadata(meta_str):
    if not meta_str:
        return {}
    if isinstance(meta_str, dict):
        return meta_str
    try:
        return json.loads(meta_str)
    except (json.JSONDecodeError, TypeError):
        return {}


app.jinja_env.filters["duration"] = _format_duration
app.jinja_env.filters["parse_meta"] = _parse_metadata


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return "ok", 200


@app.route("/")
def dashboard():
    user = _get_user()
    if not user:
        return render_template("dashboard.html", user=None, stats=None)
    with db.get_db() as conn:
        stats = db.get_dashboard_stats(conn, user)
    return render_template("dashboard.html", user=user, stats=stats)


@app.route("/wrapped")
def wrapped():
    user = _get_user()
    if not user:
        return redirect(url_for("dashboard"))
    year = request.args.get("year", type=int)
    with db.get_db() as conn:
        stats = db.get_wrapped_stats(conn, user, year)
    return render_template("wrapped.html", user=user, stats=stats,
                           year=year or datetime.now().year)


@app.route("/history")
def history():
    user = _get_user()
    if not user:
        return redirect(url_for("dashboard"))
    source = request.args.get("source")
    item_type = request.args.get("type")
    page = request.args.get("page", 1, type=int)
    limit = 50
    offset = (page - 1) * limit
    with db.get_db() as conn:
        events = db.get_history(conn, user, source, item_type, offset, limit)
    return render_template("history.html", user=user, events=events,
                           source=source, item_type=item_type, page=page)


@app.route("/admin")
def admin():
    user = _get_user()
    groups = request.headers.get("Remote-Groups", "").lower()
    is_admin = "admins" in groups
    with db.get_db() as conn:
        mappings = db.get_user_map(conn)
        poll_states = conn.execute("SELECT * FROM poll_state").fetchall()
    return render_template("admin.html", user=user, is_admin=is_admin,
                           mappings=mappings, poll_states=poll_states)


@app.route("/admin/map", methods=["POST"])
def admin_map():
    groups = request.headers.get("Remote-Groups", "").lower()
    if "admins" not in groups:
        return "Forbidden", 403
    username = request.form.get("username", "").strip().lower()
    source = request.form.get("source", "").strip()
    source_user_id = request.form.get("source_user_id", "").strip()
    if username and source and source_user_id:
        with db.get_db() as conn:
            db.set_user_map(conn, username, source, source_user_id)
    return redirect(url_for("admin"))


@app.route("/admin/poll", methods=["POST"])
def admin_poll():
    groups = request.headers.get("Remote-Groups", "").lower()
    if "admins" not in groups:
        return "Forbidden", 403
    source = request.form.get("source")
    if source == "jellyfin":
        poll_jellyfin()
    elif source == "navidrome":
        poll_navidrome()
    elif source == "romm":
        poll_romm()
    elif source == "booklore":
        poll_booklore()
    return redirect(url_for("admin"))


@app.route("/admin/backfill", methods=["POST"])
def admin_backfill():
    groups = request.headers.get("Remote-Groups", "").lower()
    if "admins" not in groups:
        return "Forbidden", 403
    source = request.form.get("source")
    # Reset backfill state to force re-backfill
    with db.get_db() as conn:
        conn.execute("UPDATE poll_state SET last_backfill = NULL WHERE source = ?",
                     (source,))
    if source == "jellyfin":
        poll_jellyfin()
    elif source == "navidrome":
        poll_navidrome()
    elif source == "romm":
        poll_romm()
    elif source == "booklore":
        poll_booklore()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
