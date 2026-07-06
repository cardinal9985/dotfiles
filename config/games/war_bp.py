import uuid
import random
import threading

from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_socketio import join_room, emit

import db
import arbiter as arbiter_mod
import stats_emit
from shared_auth import get_user

MIN_ANTE = 10
MAX_ANTE = 5000
ROUNDS_TOTAL = 5

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["♠", "♥", "♦", "♣"]
RANK_VALUE = {r: i for i, r in enumerate(RANKS, start=2)}  # 2..14

def _new_deck():
    deck = [(r, s) for r in RANKS for s in SUITS]
    random.shuffle(deck)
    return deck

_games = {}
_games_lock = threading.Lock()
_socketio = None

bp = Blueprint("war", __name__, template_folder="templates")

def _serialize(state, viewer=None):
    """Client-facing view of the current state."""
    return {
        "status":       state["status"],
        "player_a":     state["player_a"],
        "player_b":     state["player_b"],
        "a_score":      state["a_score"],
        "b_score":      state["b_score"],
        "round_index":  state["round_index"],
        "rounds_total": state["rounds_total"],
        "pot":          state["pot"],
        "last_round":   state.get("last_round"),
        "winner":       state.get("winner"),
        "arbiter":      state.get("last_arbiter"),
    }

def _draw_round(state):
    """Draw one card each. Handle ties via arbiter. Returns the round dict."""
    if len(state["deck"]) < 2:
        state["deck"] = _new_deck()
    a_card = state["deck"].pop()
    b_card = state["deck"].pop()
    a_val, b_val = RANK_VALUE[a_card[0]], RANK_VALUE[b_card[0]]

    last_arbiter = None
    if a_val > b_val:
        winner = "a"
    elif b_val > a_val:
        winner = "b"
    else:
        ruling = arbiter_mod.call_arbiter(state["player_a"], state["player_b"], reason="war_tie")
        winner = "a" if ruling["winner"] == state["player_a"] else "b"
        last_arbiter = ruling

    if winner == "a":
        state["a_score"] += 1
    else:
        state["b_score"] += 1
    state["round_index"] += 1

    round_data = {
        "a_card": a_card, "b_card": b_card,
        "winner": winner, "index": state["round_index"],
    }
    state["last_round"]    = round_data
    state["last_arbiter"]  = last_arbiter

    if state["round_index"] >= state["rounds_total"]:
        _finish(state)
    return round_data

def _finish(state):
    state["status"] = "completed"
    if state["a_score"] > state["b_score"]:
        winner_user = state["player_a"]
    elif state["b_score"] > state["a_score"]:
        winner_user = state["player_b"]
    else:
        winner_user = None
    state["winner"] = winner_user

    with db.get_db() as conn:
        if winner_user:
            db.adjust_chips(conn, winner_user, state["pot"], "war_win", state["id"])
        conn.execute(
            "UPDATE war_games SET a_score=?, b_score=?, status='completed', winner=?, completed_at=datetime('now') WHERE id=?",
            (state["a_score"], state["b_score"], winner_user, state["id"])
        )

    for role, uname in (("a", state["player_a"]), ("b", state["player_b"])):
        if not uname:
            continue
        opp = state["player_b"] if role == "a" else state["player_a"]
        stats_emit.emit(uname, "war", state["id"], item_name="WAR", metadata={
            "opponent": opp,
            "ante":     state["ante"],
            "pot":      state["pot"],
            "a_score":  state["a_score"],
            "b_score":  state["b_score"],
            "won":      uname == winner_user,
            "drew":     winner_user is None,
        })

@bp.route("/")
def lobby():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        active = conn.execute(
            "SELECT * FROM war_games WHERE status IN ('waiting','active') ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return render_template("war/lobby.html", user=user, me=me, active=active,
                           min_ante=MIN_ANTE, max_ante=MAX_ANTE)

@bp.route("/game/new", methods=["POST"])
def new_game():
    user = get_user()
    try:
        ante = int(request.form.get("ante", 100))
    except Exception:
        ante = 100
    ante = max(MIN_ANTE, min(MAX_ANTE, ante))

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ante:
            abort(400)
        db.adjust_chips(conn, user, -ante, "war_ante")

    game_id = uuid.uuid4().hex
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO war_games (id, player_a, ante, rounds_total, status) VALUES (?, ?, ?, ?, 'waiting')",
            (game_id, user, ante, ROUNDS_TOTAL)
        )
    with _games_lock:
        _games[game_id] = {
            "id":           game_id,
            "player_a":     user,
            "player_b":     None,
            "ante":         ante,
            "pot":          ante,
            "rounds_total": ROUNDS_TOTAL,
            "round_index":  0,
            "a_score":      0,
            "b_score":      0,
            "deck":         _new_deck(),
            "status":       "waiting",
        }
    return redirect(url_for("war.game", game_id=game_id))

@bp.route("/game/<game_id>")
def game(game_id):
    user = get_user()
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM war_games WHERE id=?", (game_id,)).fetchone()
    if not row:
        abort(404)
    with _games_lock:
        state = _games.get(game_id)
        if not state and row["status"] in ("waiting", "active"):
            state = {
                "id": game_id, "player_a": row["player_a"], "player_b": row["player_b"],
                "ante": row["ante"], "pot": row["ante"] * (2 if row["player_b"] else 1),
                "rounds_total": row["rounds_total"],
                "round_index": row["a_score"] + row["b_score"],
                "a_score": row["a_score"], "b_score": row["b_score"],
                "deck": _new_deck(), "status": row["status"],
            }
            _games[game_id] = state
        payload = _serialize(state) if state else None
    my_role = "a" if user == row["player_a"] else ("b" if user == row["player_b"] else None)
    return render_template("war/game.html", game_id=game_id, user=user,
                           my_role=my_role, game=row, state_payload=payload,
                           ante=row["ante"])

def register_sockets(socketio):
    global _socketio
    _socketio = socketio

    @socketio.on("join_game", namespace="/war")
    def on_join(data):
        game_id = data.get("game_id")
        user = get_user()
        if not game_id: return
        join_room(game_id)
        just_activated = False
        error = None
        with _games_lock:
            state = _games.get(game_id)
            if not state:
                return
            if state["status"] == "waiting" and user not in (state["player_a"], state["player_b"]):
                # Try to join as player B
                with db.get_db() as conn:
                    db.ensure_user(conn, user)
                    me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
                    if me["chips"] < state["ante"]:
                        error = "Not enough chips to match the ante"
                    else:
                        db.adjust_chips(conn, user, -state["ante"], "war_ante", game_id)
                        state["player_b"] = user
                        state["pot"]      = state["ante"] * 2
                        state["status"]   = "active"
                        conn.execute(
                            "UPDATE war_games SET player_b=?, status='active' WHERE id=?",
                            (user, game_id)
                        )
                        just_activated = True
        if error:
            emit("error", {"message": error})
            return

        with _games_lock:
            state = _games.get(game_id)
            payload = _serialize(state)
        emit("game_state", payload, to=game_id)

    @socketio.on("next_round", namespace="/war")
    def on_next(data):
        game_id = data.get("game_id")
        user = get_user()
        with _games_lock:
            state = _games.get(game_id)
            if not state or state["status"] != "active":
                return
            if user not in (state["player_a"], state["player_b"]):
                return
            _draw_round(state)
            payload = _serialize(state)
        emit("game_state", payload, to=game_id)
        if payload["status"] == "completed":
            emit("game_over", payload, to=game_id)
