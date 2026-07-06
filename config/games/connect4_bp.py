import uuid
import threading

from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_socketio import join_room, emit

import db
import arbiter as arbiter_mod
import stats_emit
from shared_auth import get_user

MIN_ANTE = 10
MAX_ANTE = 5000
COLS = 7
ROWS = 6

bp = Blueprint("connect4", __name__, template_folder="templates")

_games = {}
_games_lock = threading.Lock()
_socketio = None

def _empty_board():
    return [["." for _ in range(COLS)] for _ in range(ROWS)]

def _to_string(board):
    return "".join("".join(row) for row in board)

def _from_string(s):
    board = _empty_board()
    for i, c in enumerate(s):
        board[i // COLS][i % COLS] = c
    return board

def _drop(board, col, piece):
    """Drop piece into column. Returns row placed, or None if column full."""
    for row in range(ROWS):
        if board[row][col] == ".":
            board[row][col] = piece
            return row
    return None

def _check_win(board, piece):
    # Horizontal
    for r in range(ROWS):
        for c in range(COLS - 3):
            if all(board[r][c+i] == piece for i in range(4)):
                return True
    # Vertical
    for c in range(COLS):
        for r in range(ROWS - 3):
            if all(board[r+i][c] == piece for i in range(4)):
                return True
    # Diagonal /
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            if all(board[r+i][c+i] == piece for i in range(4)):
                return True
    # Diagonal \
    for r in range(3, ROWS):
        for c in range(COLS - 3):
            if all(board[r-i][c+i] == piece for i in range(4)):
                return True
    return False

def _is_full(board):
    return all(board[ROWS-1][c] != "." for c in range(COLS))

def _serialize(state):
    return {
        "status":    state["status"],
        "player_a":  state["player_a"],
        "player_b":  state["player_b"],
        "board":     _to_string(state["board"]),
        "turn":      state["turn"],       # 'a' or 'b'
        "ante":      state["ante"],
        "pot":       state["pot"],
        "winner":    state.get("winner"),
        "last_col":  state.get("last_col"),
        "last_row":  state.get("last_row"),
        "arbiter":   state.get("last_arbiter"),
    }

def _finish(state, winner_role):
    state["status"] = "completed"
    if winner_role == "a":
        winner_user = state["player_a"]
    elif winner_role == "b":
        winner_user = state["player_b"]
    else:
        winner_user = None
    state["winner"] = winner_user

    with db.get_db() as conn:
        if winner_user:
            db.adjust_chips(conn, winner_user, state["pot"], "connect4_win", state["id"])
        conn.execute(
            "UPDATE connect4_games SET board=?, status='completed', winner=?, completed_at=datetime('now') WHERE id=?",
            (_to_string(state["board"]), winner_user, state["id"])
        )

    arbiter_involved = bool(state.get("last_arbiter"))
    for role, uname in (("a", state["player_a"]), ("b", state["player_b"])):
        if not uname:
            continue
        opp = state["player_b"] if role == "a" else state["player_a"]
        stats_emit.emit(uname, "connect4", state["id"], item_name="CONNECT 4", metadata={
            "opponent":         opp,
            "ante":             state["ante"],
            "pot":              state["pot"],
            "won":              uname == winner_user,
            "arbiter_involved": arbiter_involved,
        })

@bp.route("/")
def lobby():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        active = conn.execute(
            "SELECT * FROM connect4_games WHERE status IN ('waiting','active') ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return render_template("connect4/lobby.html", user=user, me=me, active=active,
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
        db.adjust_chips(conn, user, -ante, "connect4_ante")

    game_id = uuid.uuid4().hex
    board = _empty_board()
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO connect4_games (id, player_a, ante, status, board, turn) VALUES (?, ?, ?, 'waiting', ?, 'a')",
            (game_id, user, ante, _to_string(board))
        )

    with _games_lock:
        _games[game_id] = {
            "id":       game_id,
            "player_a": user, "player_b": None,
            "board":    board,
            "turn":     "a",
            "ante":     ante,
            "pot":      ante,
            "status":   "waiting",
        }
    return redirect(url_for("connect4.game", game_id=game_id))

@bp.route("/game/<game_id>")
def game(game_id):
    user = get_user()
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM connect4_games WHERE id=?", (game_id,)).fetchone()
    if not row:
        abort(404)
    with _games_lock:
        state = _games.get(game_id)
        if not state and row["status"] in ("waiting", "active"):
            state = {
                "id": game_id, "player_a": row["player_a"], "player_b": row["player_b"],
                "board": _from_string(row["board"]) if row["board"] else _empty_board(),
                "turn": row["turn"] or "a",
                "ante": row["ante"], "pot": row["ante"] * (2 if row["player_b"] else 1),
                "status": row["status"],
            }
            _games[game_id] = state
        payload = _serialize(state) if state else None
    my_role = "a" if user == row["player_a"] else ("b" if user == row["player_b"] else None)
    return render_template("connect4/game.html", game_id=game_id, user=user,
                           my_role=my_role, game=row, state_payload=payload,
                           cols=COLS, rows=ROWS)

def register_sockets(socketio):
    global _socketio
    _socketio = socketio

    @socketio.on("join_game", namespace="/connect4")
    def on_join(data):
        game_id = data.get("game_id")
        user = get_user()
        if not game_id: return
        join_room(game_id)
        error = None
        with _games_lock:
            state = _games.get(game_id)
            if not state:
                return
            if state["status"] == "waiting" and user not in (state["player_a"], state["player_b"]):
                with db.get_db() as conn:
                    db.ensure_user(conn, user)
                    me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
                    if me["chips"] < state["ante"]:
                        error = "Not enough chips to match the ante"
                    else:
                        db.adjust_chips(conn, user, -state["ante"], "connect4_ante", game_id)
                        state["player_b"] = user
                        state["pot"]      = state["ante"] * 2
                        state["status"]   = "active"
                        conn.execute(
                            "UPDATE connect4_games SET player_b=?, status='active' WHERE id=?",
                            (user, game_id)
                        )
        if error:
            emit("error", {"message": error}); return
        with _games_lock:
            payload = _serialize(_games[game_id])
        emit("game_state", payload, to=game_id)

    @socketio.on("drop", namespace="/connect4")
    def on_drop(data):
        game_id = data.get("game_id")
        col     = int(data.get("col", -1))
        user    = get_user()

        with _games_lock:
            state = _games.get(game_id)
            if not state or state["status"] != "active":
                return
            if not (0 <= col < COLS):
                emit("error", {"message": "Bad column"}); return
            expected_user = state["player_a"] if state["turn"] == "a" else state["player_b"]
            if user != expected_user:
                emit("error", {"message": "Not your turn"}); return

            piece = state["turn"]
            row = _drop(state["board"], col, piece)
            if row is None:
                emit("error", {"message": "Column full"}); return
            state["last_col"] = col
            state["last_row"] = row

            winner_role = None
            if _check_win(state["board"], piece):
                winner_role = piece
            elif _is_full(state["board"]):
                # Draw: Arbiter decides who takes the pot
                ruling = arbiter_mod.call_arbiter(state["player_a"], state["player_b"], reason="connect4_draw")
                winner_role = "a" if ruling["winner"] == state["player_a"] else "b"
                state["last_arbiter"] = ruling
            else:
                state["turn"] = "b" if piece == "a" else "a"

            if winner_role:
                _finish(state, winner_role)
            payload = _serialize(state)

            with db.get_db() as conn:
                conn.execute("UPDATE connect4_games SET board=?, turn=? WHERE id=?",
                             (_to_string(state["board"]), state["turn"], game_id))

        emit("game_state", payload, to=game_id)
        if payload["status"] == "completed":
            emit("game_over", payload, to=game_id)
