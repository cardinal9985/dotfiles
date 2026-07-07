import json
import random
import uuid

from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

PLAYER = "X"
BOT    = "O"

LINES = (
    (0,1,2), (3,4,5), (6,7,8),
    (0,3,6), (1,4,7), (2,5,8),
    (0,4,8), (2,4,6),
)

DIFFICULTIES = {
    "easy":   {"entry": 10, "win":  25, "draw": 10},
    "medium": {"entry": 10, "win":  50, "draw": 15},
    "hard":   {"entry": 10, "win": 500, "draw": 12},
}

def _check_winner(board):
    for a, b, c in LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(c is not None for c in board):
        return "draw"
    return None

def _empty(board):
    return [i for i in range(9) if board[i] is None]

def _minimax(board, to_move, maximizer, depth=0):
    w = _check_winner(board)
    if w == maximizer:   return (10 - depth, None)
    if w and w != "draw": return (depth - 10, None)
    if w == "draw":      return (0, None)
    best_score = None
    best_move  = None
    for cell in _empty(board):
        board[cell] = to_move
        score, _ = _minimax(board, PLAYER if to_move == BOT else BOT, maximizer, depth + 1)
        board[cell] = None
        if to_move == maximizer:
            if best_score is None or score > best_score:
                best_score, best_move = score, cell
        else:
            if best_score is None or score < best_score:
                best_score, best_move = score, cell
    return (best_score, best_move)

def _bot_move(board, difficulty):
    empty = _empty(board)
    if not empty:
        return None
    if difficulty == "easy":
        return random.choice(empty)
    for cell in empty:
        board[cell] = BOT
        if _check_winner(board) == BOT:
            board[cell] = None
            return cell
        board[cell] = None
    for cell in empty:
        board[cell] = PLAYER
        if _check_winner(board) == PLAYER:
            board[cell] = None
            return cell
        board[cell] = None
    if difficulty == "medium":
        if 4 in empty:
            return 4
        corners = [c for c in (0, 2, 6, 8) if c in empty]
        if corners:
            return random.choice(corners)
        return random.choice(empty)
    _, move = _minimax(list(board), BOT, BOT)
    return move if move is not None else random.choice(empty)

bp = Blueprint("tictactoe", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        active = conn.execute(
            "SELECT * FROM tictactoe_games WHERE username=? AND status='active' ORDER BY created_at DESC LIMIT 1",
            (user,)
        ).fetchone()
        recent = conn.execute(
            "SELECT * FROM tictactoe_games WHERE username=? AND status!='active' ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
        stats = conn.execute(
            """SELECT difficulty,
                      SUM(CASE WHEN status='won'  THEN 1 ELSE 0 END) AS wins,
                      SUM(CASE WHEN status='lost' THEN 1 ELSE 0 END) AS losses,
                      SUM(CASE WHEN status='draw' THEN 1 ELSE 0 END) AS draws
                 FROM tictactoe_games
                WHERE username=?
             GROUP BY difficulty""",
            (user,)
        ).fetchall()
    active_board = json.loads(active["board_json"]) if active else [None] * 9
    return render_template(
        "tictactoe/table.html",
        user=user, me=me,
        active_id=active["id"] if active else None,
        active_board=active_board,
        active_difficulty=active["difficulty"] if active else None,
        recent=recent,
        stats={s["difficulty"]: s for s in stats},
        difficulties=DIFFICULTIES,
    )

@bp.route("/api/start", methods=["POST"])
def api_start():
    user = get_user()
    payload = request.get_json(silent=True) or {}
    diff = payload.get("difficulty", "medium")
    if diff not in DIFFICULTIES:
        return jsonify({"error": "Bad difficulty"}), 400
    entry = DIFFICULTIES[diff]["entry"]

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < entry:
            return jsonify({"error": f"Need {entry} tickets"}), 400
        db.adjust_chips(conn, user, -entry, f"ttt_entry_{diff}")
        # abandon any prior active game (no refund - they left it)
        conn.execute(
            "UPDATE tictactoe_games SET status='abandoned', completed_at=datetime('now') WHERE username=? AND status='active'",
            (user,)
        )
        gid = uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO tictactoe_games (id, username, difficulty, entry_fee) VALUES (?, ?, ?, ?)",
            (gid, user, diff, entry)
        )
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    return jsonify({
        "game_id":     gid,
        "board":       [None] * 9,
        "status":      "active",
        "difficulty":  diff,
        "new_balance": new_balance,
    })

@bp.route("/api/move", methods=["POST"])
def api_move():
    user = get_user()
    payload = request.get_json(silent=True) or {}
    gid = payload.get("game_id")
    cell = payload.get("cell")
    if not isinstance(cell, int) or not (0 <= cell < 9):
        return jsonify({"error": "Bad cell"}), 400

    with db.get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tictactoe_games WHERE id=? AND username=?", (gid, user)
        ).fetchone()
        if not row:
            return jsonify({"error": "Game not found"}), 404
        if row["status"] != "active":
            return jsonify({"error": "Game already ended"}), 400
        board = json.loads(row["board_json"])
        if board[cell] is not None:
            return jsonify({"error": "Cell taken"}), 400

        board[cell] = PLAYER
        winner = _check_winner(board)
        bot_cell = None
        if winner is None:
            bot_cell = _bot_move(board, row["difficulty"])
            if bot_cell is not None:
                board[bot_cell] = BOT
                winner = _check_winner(board)

        if winner == PLAYER:
            status = "won"
        elif winner == BOT:
            status = "lost"
        elif winner == "draw":
            status = "draw"
        else:
            status = "active"

        payout = 0
        if status == "won":
            payout = DIFFICULTIES[row["difficulty"]]["win"]
        elif status == "draw":
            payout = DIFFICULTIES[row["difficulty"]]["draw"]
        if payout > 0:
            db.adjust_chips(conn, user, payout, f"ttt_{status}_{row['difficulty']}")

        conn.execute(
            "UPDATE tictactoe_games SET board_json=?, status=?, payout=?, completed_at=CASE WHEN ? != 'active' THEN datetime('now') ELSE completed_at END WHERE id=?",
            (json.dumps(board), status, payout, status, gid)
        )
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

        if status != "active":
            stats_emit.emit(user, "tictactoe", gid, item_name=f"TIC-TAC-TOE {row['difficulty'].upper()}", metadata={
                "difficulty": row["difficulty"],
                "result":     status,
                "payout":     payout,
            })

    return jsonify({
        "board":        board,
        "bot_cell":     bot_cell,
        "status":       status,
        "payout":       payout,
        "new_balance":  new_balance,
    })
