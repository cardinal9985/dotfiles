import json
import random
import threading
import time as _time
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify
from flask_socketio import join_room, emit

import db
import stats_emit
from shared_auth import get_user

MIN_ENTRY = 10
MAX_ENTRY = 1000
MAX_DUCKS = 6
FINISH_LINE = 100
TICK_MS = 200

_races = {}
_races_lock = threading.Lock()
_socketio = None

DUCK_NAMES = ["QUACKENSHTEIN", "SIR PADDLES", "WEBBED FEAR", "MOTHERGOOSE", "BEAK REAPER", "USG QUACK"]

bp = Blueprint("duckrace", __name__, template_folder="templates")


def _serialize(race):
    return {
        "id":          race["id"],
        "creator":     race["creator"],
        "entry_fee":   race["entry_fee"],
        "pot":         race["pot"],
        "status":      race["status"],
        "ducks":       race["ducks"],   # list of {n, user, name, pos}
        "winner":      race.get("winner"),
        "winner_duck": race.get("winner_duck"),
    }


def _run_race(race_id):
    with _races_lock:
        race = _races.get(race_id)
        if not race or race["status"] != "active":
            return

    while True:
        _time.sleep(TICK_MS / 1000)
        with _races_lock:
            race = _races.get(race_id)
            if not race or race["status"] != "active":
                return
            for duck in race["ducks"]:
                if duck["user"] is None:
                    continue
                # Random 1-4 units per tick, biased so someone finishes in ~15s
                duck["pos"] += random.randint(1, 5)
                if duck["pos"] >= FINISH_LINE:
                    duck["pos"] = FINISH_LINE
                    race["winner"] = duck["user"]
                    race["winner_duck"] = duck
                    race["status"] = "completed"
                    break
            payload = _serialize(race)
        _socketio.emit("race_tick", payload, to=race_id, namespace="/duckrace")
        if race["status"] == "completed":
            _finish_race(race_id)
            return


def _finish_race(race_id):
    with _races_lock:
        race = _races.get(race_id)
        if not race:
            return
        winner_user = race.get("winner")
        pot = race["pot"]

    if winner_user:
        with db.get_db() as conn:
            db.adjust_chips(conn, winner_user, pot, "duckrace_win", race_id)
        stats_emit.emit(winner_user, "duckrace", race_id, item_name="DUCK RACE", metadata={
            "pot": pot, "won": True, "duck": race["winner_duck"]["name"],
        })
        for d in race["ducks"]:
            if d["user"] and d["user"] != winner_user:
                stats_emit.emit(d["user"], "duckrace", race_id, item_name="DUCK RACE", metadata={
                    "pot": pot, "won": False, "duck": d["name"],
                })

    with db.get_db() as conn:
        conn.execute(
            "UPDATE duckrace_games SET status='completed', winner=?, ducks=?, completed_at=datetime('now') WHERE id=?",
            (winner_user, json.dumps(race["ducks"]), race_id)
        )

    _socketio.emit("race_over", _serialize(race), to=race_id, namespace="/duckrace")


@bp.route("/")
def lobby():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        active = conn.execute(
            "SELECT * FROM duckrace_games WHERE status IN ('waiting','active') ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return render_template("duckrace/lobby.html", user=user, me=me, active=active,
                           min_entry=MIN_ENTRY, max_entry=MAX_ENTRY, max_ducks=MAX_DUCKS)


@bp.route("/race/new", methods=["POST"])
def new_race():
    user = get_user()
    try:
        entry_fee = int(request.form.get("entry_fee", 50))
    except Exception:
        entry_fee = 50
    entry_fee = max(MIN_ENTRY, min(MAX_ENTRY, entry_fee))

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < entry_fee:
            abort(400)
        db.adjust_chips(conn, user, -entry_fee, "duckrace_entry")

    race_id = uuid.uuid4().hex
    ducks = [{"n": i + 1, "name": DUCK_NAMES[i], "user": None, "pos": 0} for i in range(MAX_DUCKS)]
    ducks[0]["user"] = user  # creator picks duck 1

    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO duckrace_games (id, creator, entry_fee, pot, ducks, status) VALUES (?, ?, ?, ?, ?, 'waiting')",
            (race_id, user, entry_fee, entry_fee, json.dumps(ducks))
        )

    with _races_lock:
        _races[race_id] = {
            "id": race_id, "creator": user, "entry_fee": entry_fee,
            "pot": entry_fee, "ducks": ducks, "status": "waiting",
        }
    return redirect(url_for("duckrace.race", race_id=race_id))


@bp.route("/race/<race_id>")
def race(race_id):
    user = get_user()
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM duckrace_games WHERE id=?", (race_id,)).fetchone()
    if not row:
        abort(404)

    with _races_lock:
        race_state = _races.get(race_id)
        if not race_state and row["status"] in ("waiting", "active"):
            race_state = {
                "id": race_id, "creator": row["creator"],
                "entry_fee": row["entry_fee"], "pot": row["pot"],
                "ducks": json.loads(row["ducks"]) if row["ducks"] else [],
                "status": row["status"],
            }
            _races[race_id] = race_state
        payload = _serialize(race_state) if race_state else None

    return render_template("duckrace/race.html", race_id=race_id, user=user,
                           race=row, state_payload=payload)


def register_sockets(socketio):
    global _socketio
    _socketio = socketio

    @socketio.on("join_race", namespace="/duckrace")
    def on_join(data):
        race_id = data.get("race_id")
        user = get_user()
        if not race_id:
            return
        join_room(race_id)
        error = None
        just_joined = False
        with _races_lock:
            race = _races.get(race_id)
            if not race:
                return
            if race["status"] == "waiting" and not any(d["user"] == user for d in race["ducks"]):
                with db.get_db() as conn:
                    db.ensure_user(conn, user)
                    me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
                    if me["chips"] < race["entry_fee"]:
                        error = "Not enough tickets to enter"
                    else:
                        # Assign first empty duck slot
                        for duck in race["ducks"]:
                            if duck["user"] is None:
                                duck["user"] = user
                                just_joined = True
                                break
                        if not just_joined:
                            error = "Race is full"
                        else:
                            db.adjust_chips(conn, user, -race["entry_fee"], "duckrace_entry", race_id)
                            race["pot"] += race["entry_fee"]
                            conn.execute(
                                "UPDATE duckrace_games SET ducks=?, pot=? WHERE id=?",
                                (json.dumps(race["ducks"]), race["pot"], race_id)
                            )
        if error:
            emit("error", {"message": error})
            return
        with _races_lock:
            payload = _serialize(_races[race_id])
        emit("race_state", payload, to=race_id)

    @socketio.on("start_race", namespace="/duckrace")
    def on_start(data):
        race_id = data.get("race_id")
        user = get_user()
        with _races_lock:
            race = _races.get(race_id)
            if not race or race["status"] != "waiting":
                return
            if user != race["creator"]:
                emit("error", {"message": "Only the creator can start"})
                return
            filled = sum(1 for d in race["ducks"] if d["user"] is not None)
            if filled < 2:
                emit("error", {"message": "Need at least 2 ducks in the race"})
                return
            race["status"] = "active"
            with db.get_db() as conn:
                conn.execute("UPDATE duckrace_games SET status='active' WHERE id=?", (race_id,))
        _socketio.emit("race_state", _serialize(race), to=race_id, namespace="/duckrace")
        threading.Thread(target=_run_race, args=(race_id,), daemon=True).start()
