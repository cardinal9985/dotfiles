import os
import uuid
import json
import threading
import urllib.request
from datetime import datetime

import chess
import chess.engine
from flask import Flask, render_template, request, redirect, url_for, abort, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit

import db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ishimura-chess-dev")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "stockfish")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
DB_PATH = os.environ.get("CHESS_DB_PATH", "/tmp/chess.db")
db.DB_PATH = DB_PATH

# In-memory game state (board + engine per active game)
_games = {}
_games_lock = threading.Lock()

def get_user():
    return request.headers.get("Remote-User", "").strip()

# ── Helpers ──────────────────────────────────────────────────────────────────

def _legal_moves_map(board):
    """Returns {from_sq: [to_sq, ...]} for the side to move."""
    moves = {}
    for move in board.legal_moves:
        f = chess.square_name(move.from_square)
        t = chess.square_name(move.to_square)
        moves.setdefault(f, []).append(t)
    return moves

def _board_state(game_id):
    """Serialise board state for the client."""
    with _games_lock:
        g = _games.get(game_id)
        if not g:
            return None
        board = g["board"]
        return {
            "fen":          board.fen(),
            "turn":         "white" if board.turn == chess.WHITE else "black",
            "legal_moves":  _legal_moves_map(board),
            "in_check":     board.is_check(),
            "is_game_over": board.is_game_over(),
            "white":        g["white"],
            "black":        g["black"],
            "white_is_ai":  g["white_is_ai"],
            "black_is_ai":  g["black_is_ai"],
            "move_stack":   [m.uci() for m in board.move_stack],
            "status":       g["status"],
        }

def _finish_game(game_id, result, pgn):
    """Persist result, update stats, notify Discord."""
    with get_db_conn() as conn:
        conn.execute(
            "UPDATE games SET status='completed', result=?, pgn=?, moves=?, completed_at=? WHERE id=?",
            (result, pgn, " ".join(m.uci() for m in _games[game_id]["board"].move_stack),
             datetime.utcnow().isoformat(), game_id)
        )
        db.record_result(conn, game_id, result)

    _discord_notify(game_id, result)

    with _games_lock:
        g = _games.get(game_id, {})
        engine = g.get("engine")
        if engine:
            try:
                engine.quit()
            except Exception:
                pass
        _games.pop(game_id, None)

def _discord_notify(game_id, result):
    if not DISCORD_WEBHOOK:
        return
    with get_db_conn() as conn:
        game = conn.execute("SELECT white, black, white_is_ai, black_is_ai FROM games WHERE id=?", (game_id,)).fetchone()
    if not game:
        return

    white = "AI" if game["white_is_ai"] else (game["white"] or "?")
    black = "AI" if game["black_is_ai"] else (game["black"] or "?")
    labels = {
        "white_wins": f"**{white}** defeated {black}",
        "black_wins": f"**{black}** defeated {white}",
        "draw":       f"{white} and {black} drew",
    }
    label = labels.get(result, f"Game ended: {result}")
    payload = json.dumps({"content": f"USG ISHIMURA CHESS | {label}"}).encode()
    try:
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def _ai_move(game_id):
    """Run Stockfish in a thread and emit the resulting board state."""
    with _games_lock:
        g = _games.get(game_id)
        if not g:
            return
        board = g["board"].copy()
        engine = g.get("engine")
        level = g.get("ai_level", 5)

    if not engine:
        return

    try:
        engine.configure({"Skill Level": level})
        result = engine.play(board, chess.engine.Limit(time=0.5))
        move = result.move
    except Exception:
        return

    with _games_lock:
        g = _games.get(game_id)
        if not g or g["status"] != "active":
            return
        g["board"].push(move)
        board = g["board"]

    with get_db_conn() as conn:
        conn.execute("UPDATE games SET moves=? WHERE id=?",
                     (" ".join(m.uci() for m in board.move_stack), game_id))

    state = _board_state(game_id)
    socketio.emit("game_state", state, to=game_id)

    if board.is_game_over():
        outcome = board.outcome()
        result = _outcome_to_result(outcome)
        pgn = _board_to_pgn(board, game_id)
        _finish_game(game_id, result, pgn)
        socketio.emit("game_over", {"result": result, "pgn": pgn}, to=game_id)

def _outcome_to_result(outcome):
    if outcome is None:
        return "draw"
    if outcome.winner == chess.WHITE:
        return "white_wins"
    if outcome.winner == chess.BLACK:
        return "black_wins"
    return "draw"

def _board_to_pgn(board, game_id):
    """Very minimal PGN export."""
    game = chess.pgn.Game.from_board(board)
    return str(game)

def get_db_conn():
    return db.get_db()

# ── Routes ───────────────────────────────────────────────────────────────────

@app.before_request
def require_auth():
    if not get_user() and not app.debug:
        return "Unauthorized", 401

@app.route("/")
def index():
    user = get_user()
    with get_db_conn() as conn:
        db.ensure_user(conn, user)
        active = db.get_active_games(conn)
        leaders = db.get_leaderboard(conn)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
    return render_template("index.html", user=user, active_games=active,
                           leaderboard=leaders, me=me)

@app.route("/game/new", methods=["POST"])
def new_game():
    user = get_user()
    game_type = request.form.get("type", "human")
    color = request.form.get("color", "white")
    ai_level = int(request.form.get("ai_level", 5))
    game_id = uuid.uuid4().hex

    white = black = None
    white_is_ai = black_is_ai = False

    if game_type == "ai":
        if color == "white":
            white, black = user, None
            black_is_ai = True
        else:
            white, black = None, user
            white_is_ai = True
        status = "active"
    else:
        if color == "white":
            white = user
        else:
            black = user
        status = "waiting"

    with get_db_conn() as conn:
        db.ensure_user(conn, user)
        conn.execute(
            "INSERT INTO games (id, white, black, white_is_ai, black_is_ai, ai_level, status) VALUES (?,?,?,?,?,?,?)",
            (game_id, white, black, int(white_is_ai), int(black_is_ai), ai_level, status)
        )

    board = chess.Board()
    engine = None
    if game_type == "ai":
        try:
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception:
            engine = None

    with _games_lock:
        _games[game_id] = {
            "board":       board,
            "white":       white,
            "black":       black,
            "white_is_ai": white_is_ai,
            "black_is_ai": black_is_ai,
            "ai_level":    ai_level,
            "engine":      engine,
            "status":      status,
            "draw_offered_by": None,
        }

    if game_type == "ai" and white_is_ai:
        threading.Thread(target=_ai_move, args=(game_id,), daemon=True).start()

    return redirect(url_for("game", game_id=game_id))

@app.route("/game/<game_id>")
def game(game_id):
    user = get_user()
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
    if not row:
        abort(404)

    # Load into memory if not already there (server restart recovery)
    with _games_lock:
        if game_id not in _games and row["status"] in ("waiting", "active"):
            board = chess.Board()
            for uci in (row["moves"] or "").split():
                if uci:
                    board.push(chess.Move.from_uci(uci))
            _games[game_id] = {
                "board":       board,
                "white":       row["white"],
                "black":       row["black"],
                "white_is_ai": bool(row["white_is_ai"]),
                "black_is_ai": bool(row["black_is_ai"]),
                "ai_level":    row["ai_level"],
                "engine":      None,
                "status":      row["status"],
                "draw_offered_by": None,
            }

    my_color = None
    if row["white"] == user:
        my_color = "white"
    elif row["black"] == user:
        my_color = "black"

    return render_template("game.html", game_id=game_id, user=user,
                           my_color=my_color, game=row)

@app.route("/analysis/<game_id>")
def analysis(game_id):
    user = get_user()
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
        existing = conn.execute(
            "SELECT * FROM game_analysis WHERE game_id=? ORDER BY move_number",
            (game_id,)
        ).fetchall()
    if not row:
        abort(404)
    return render_template("analysis.html", game_id=game_id, user=user,
                           game=row, analysis=existing)

@app.route("/profile/<username>")
def profile(username):
    user = get_user()
    with get_db_conn() as conn:
        stats = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        games = db.get_user_games(conn, username)
    if not stats:
        abort(404)
    return render_template("profile.html", user=user, subject=username,
                           stats=stats, games=games)

@app.route("/api/leaderboard")
def api_leaderboard():
    with get_db_conn() as conn:
        leaders = db.get_leaderboard(conn)
    return jsonify([dict(r) for r in leaders])

@app.route("/api/fens", methods=["POST"])
def api_fens():
    moves = request.json.get("moves", [])
    board = chess.Board()
    fens = [board.fen()]
    for uci in moves:
        try:
            board.push(chess.Move.from_uci(uci))
            fens.append(board.fen())
        except Exception:
            break
    return jsonify({"fens": fens})

# ── SocketIO events ───────────────────────────────────────────────────────────

@socketio.on("join_game")
def on_join(data):
    game_id = data.get("game_id")
    user = request.headers.get("Remote-User", "").strip()
    if not game_id:
        return

    join_room(game_id)

    with _games_lock:
        g = _games.get(game_id)
        if not g:
            return

        # Second human player joining a waiting game
        if g["status"] == "waiting" and user not in (g["white"], g["black"]):
            if g["white"] is None:
                g["white"] = user
            elif g["black"] is None:
                g["black"] = user
            g["status"] = "active"

            with get_db_conn() as conn:
                db.ensure_user(conn, user)
                conn.execute(
                    "UPDATE games SET white=?, black=?, status='active' WHERE id=?",
                    (g["white"], g["black"], game_id)
                )

    state = _board_state(game_id)
    emit("game_state", state, to=game_id)

@socketio.on("make_move")
def on_move(data):
    game_id = data.get("game_id")
    move_uci = data.get("move")
    promotion = data.get("promotion", "q")
    user = request.headers.get("Remote-User", "").strip()

    with _games_lock:
        g = _games.get(game_id)
        if not g or g["status"] != "active":
            emit("error", {"message": "Game not active"})
            return

        board = g["board"]
        if board.turn == chess.WHITE and g["white"] != user:
            emit("error", {"message": "Not your turn"})
            return
        if board.turn == chess.BLACK and g["black"] != user:
            emit("error", {"message": "Not your turn"})
            return

        try:
            # Handle promotion
            if len(move_uci) == 4:
                from_sq = chess.parse_square(move_uci[:2])
                to_sq   = chess.parse_square(move_uci[2:])
                piece   = board.piece_at(from_sq)
                if piece and piece.piece_type == chess.PAWN:
                    rank = chess.square_rank(to_sq)
                    if rank in (0, 7):
                        move_uci += promotion
            move = chess.Move.from_uci(move_uci)
            if move not in board.legal_moves:
                emit("error", {"message": "Illegal move"})
                return
            board.push(move)
        except Exception:
            emit("error", {"message": "Invalid move"})
            return

        ai_to_move = (board.turn == chess.WHITE and g["white_is_ai"]) or \
                     (board.turn == chess.BLACK and g["black_is_ai"])
        is_over = board.is_game_over()

    with get_db_conn() as conn:
        conn.execute("UPDATE games SET moves=? WHERE id=?",
                     (" ".join(m.uci() for m in board.move_stack), game_id))

    state = _board_state(game_id)
    emit("game_state", state, to=game_id)

    if is_over:
        outcome = board.outcome()
        result = _outcome_to_result(outcome)
        pgn = _board_to_pgn(board, game_id)
        _finish_game(game_id, result, pgn)
        emit("game_over", {"result": result, "pgn": pgn}, to=game_id)
    elif ai_to_move:
        threading.Thread(target=_ai_move, args=(game_id,), daemon=True).start()

@socketio.on("resign")
def on_resign(data):
    game_id = data.get("game_id")
    user = request.headers.get("Remote-User", "").strip()

    with _games_lock:
        g = _games.get(game_id)
        if not g or g["status"] != "active":
            return
        result = "black_wins" if g["white"] == user else "white_wins"
        g["status"] = "completed"

    board = g["board"]
    pgn = _board_to_pgn(board, game_id)
    _finish_game(game_id, result, pgn)
    emit("game_over", {"result": result, "pgn": pgn, "resigned": user}, to=game_id)

@socketio.on("offer_draw")
def on_offer_draw(data):
    game_id = data.get("game_id")
    user = request.headers.get("Remote-User", "").strip()
    with _games_lock:
        g = _games.get(game_id)
        if not g or g["status"] != "active":
            return
        g["draw_offered_by"] = user
    emit("draw_offered", {"by": user}, to=game_id)

@socketio.on("accept_draw")
def on_accept_draw(data):
    game_id = data.get("game_id")
    user = request.headers.get("Remote-User", "").strip()
    with _games_lock:
        g = _games.get(game_id)
        if not g or g["status"] != "active" or g["draw_offered_by"] == user:
            return
        g["status"] = "completed"

    board = g["board"]
    pgn = _board_to_pgn(board, game_id)
    _finish_game(game_id, "draw", pgn)
    emit("game_over", {"result": "draw", "pgn": pgn}, to=game_id)

@socketio.on("request_analysis")
def on_request_analysis(data):
    game_id = data.get("game_id")
    threading.Thread(target=_run_analysis, args=(game_id,), daemon=True).start()

def _run_analysis(game_id):
    with get_db_conn() as conn:
        row = conn.execute("SELECT moves FROM games WHERE id=?", (game_id,)).fetchone()
    if not row or not row["moves"]:
        return

    move_ucis = row["moves"].split()
    board = chess.Board()

    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except Exception:
        socketio.emit("analysis_error", {"message": "Stockfish unavailable"}, to=game_id)
        return

    try:
        with get_db_conn() as conn:
            conn.execute("DELETE FROM game_analysis WHERE game_id=?", (game_id,))

        for i, uci in enumerate(move_ucis):
            info = engine.analyse(board, chess.engine.Limit(depth=15))
            score = info["score"].white()
            eval_cp = score.score(mate_score=10000) if score is not None else None
            best = info.get("pv", [None])[0]
            best_uci = best.uci() if best else None

            with get_db_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO game_analysis (game_id, move_number, move_uci, evaluation, best_move) VALUES (?,?,?,?,?)",
                    (game_id, i, uci, eval_cp, best_uci)
                )

            socketio.emit("analysis_update", {
                "move_number": i,
                "move_uci":    uci,
                "evaluation":  eval_cp,
                "best_move":   best_uci,
            }, to=game_id)

            board.push(chess.Move.from_uci(uci))

        socketio.emit("analysis_complete", {}, to=game_id)
    finally:
        engine.quit()


if __name__ == "__main__":
    db.init_db()
    import chess.pgn
    socketio.run(app, host="0.0.0.0", port=5001, debug=False)
