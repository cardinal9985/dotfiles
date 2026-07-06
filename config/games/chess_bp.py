import os
import uuid
import json
import threading
import random
import time as _time
import urllib.request
from datetime import datetime

import chess
import chess.engine
import chess.pgn
import chess.variant
from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify, Response
from flask_socketio import join_room, emit

import db
import stats_emit
from shared_auth import get_user

STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "stockfish")
DISCORD_WEBHOOK = os.environ.get("CHESS_DISCORD_WEBHOOK", "")

BOTS = {
    "rookie":    {"name": "ROOKIE",    "level":  1, "elo": "~400",  "desc": "Fresh off the shuttle"},
    "ensign":    {"name": "ENSIGN",    "level":  5, "elo": "~900",  "desc": "Deck crew, plays weekly"},
    "officer":   {"name": "OFFICER",   "level": 10, "elo": "~1350", "desc": "Bridge crew, sharper tactics"},
    "commander": {"name": "COMMANDER", "level": 15, "elo": "~1800", "desc": "Executive officer, tournament-level"},
    "captain":   {"name": "CAPTAIN",   "level": 20, "elo": "~2200", "desc": "The Marker's chosen"},
}

VARIANTS = {
    "standard":    {"name": "STANDARD",     "desc": "Classical chess"},
    "chess960":    {"name": "CHESS 960",    "desc": "Randomized back-rank starting position"},
    "koth":        {"name": "KING OF HILL", "desc": "Win by reaching any of the 4 center squares"},
    "3check":      {"name": "3-CHECK",      "desc": "Win by delivering 3 checks (or normal mate)"},
    "atomic":      {"name": "ATOMIC",       "desc": "Captures explode adjacent non-pawn pieces"},
    "horde":       {"name": "HORDE",        "desc": "White has 36 pawns vs Black's full army"},
    "duck":        {"name": "DUCK CHESS",   "desc": "Place a duck each turn - blocks all moves. Capture the king to win"},
}

TIME_CONTROLS = {
    "unlimited": {"name": "UNLIMITED", "initial_ms":       0, "increment_ms":    0},
    "bullet":    {"name": "BULLET 1+0", "initial_ms":  60000, "increment_ms":    0},
    "blitz":     {"name": "BLITZ 3+2",  "initial_ms": 180000, "increment_ms": 2000},
    "rapid":     {"name": "RAPID 10+5", "initial_ms": 600000, "increment_ms": 5000},
}

PGN_VARIANT_TAGS = {
    "chess960": "Chess960",
    "koth":     "King of the Hill",
    "3check":   "Three-check",
    "atomic":   "Atomic",
    "horde":    "Horde",
    "duck":     "Duck",
}

def _duck_move_legal(board, move, duck_sq):
    if duck_sq is not None and move.to_square == duck_sq:
        return False
    piece = board.piece_at(move.from_square)
    if not piece:
        return False
    if duck_sq is not None:
        if piece.piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            if duck_sq in chess.SquareSet.between(move.from_square, move.to_square):
                return False
        elif piece.piece_type == chess.PAWN and \
             abs(chess.square_rank(move.to_square) - chess.square_rank(move.from_square)) == 2:
            if duck_sq == (move.from_square + move.to_square) // 2:
                return False
    if move in board.pseudo_legal_moves:
        return True
    target = board.piece_at(move.to_square)
    if target and target.piece_type == chess.KING and target.color != board.turn:
        adjacent = duck_sq is None or (duck_sq not in chess.SquareSet.between(move.from_square, move.to_square))
        return adjacent
    return False

def _duck_king_captured(board):
    return board.king(chess.WHITE) is None or board.king(chess.BLACK) is None

def make_board(variant, chess960_fen=None):
    if variant == "chess960":
        return chess.Board.from_chess960_pos(chess960_fen) if chess960_fen else chess.Board(chess960=True)
    if variant == "koth":     return chess.variant.KingOfTheHillBoard()
    if variant == "3check":   return chess.variant.ThreeCheckBoard()
    if variant == "atomic":   return chess.variant.AtomicBoard()
    if variant == "horde":    return chess.variant.HordeBoard()
    if variant == "duck":     return chess.Board()
    return chess.Board()

_games = {}
_games_lock = threading.Lock()
_socketio = None
STALE_TIMEOUT_SEC = 3600

def _touch(g):
    g["last_activity"] = _time.monotonic()

def _cleanup_stale_games():
    while True:
        _time.sleep(600)
        now = _time.monotonic()
        engines_to_quit = []
        with _games_lock:
            for gid in list(_games.keys()):
                g = _games[gid]
                last = g.get("last_activity", now)
                if now - last > STALE_TIMEOUT_SEC:
                    engine = g.get("engine")
                    if engine:
                        engines_to_quit.append(engine)
                    _games.pop(gid, None)
        for e in engines_to_quit:
            try: e.quit()
            except Exception: pass

threading.Thread(target=_cleanup_stale_games, daemon=True).start()

def _legal_moves_map(board):
    moves = {}
    for move in board.legal_moves:
        f = chess.square_name(move.from_square)
        t = chess.square_name(move.to_square)
        moves.setdefault(f, []).append(t)
    return moves

def _check_counts(board):
    if isinstance(board, chess.variant.ThreeCheckBoard):
        return {"white": board.remaining_checks[chess.WHITE], "black": board.remaining_checks[chess.BLACK]}
    return None

def _board_state(game_id):
    with _games_lock:
        g = _games.get(game_id)
        if not g:
            return None
        board = g["board"]
        wt, bt = _current_times(g)
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
            "bot_name":     g.get("bot_name", ""),
            "move_stack":   [m.uci() for m in board.move_stack],
            "san_stack":    list(g.get("san_stack", [])),
            "status":       g["status"],
            "variant":      g.get("variant", "standard"),
            "time_control": g.get("time_control", "unlimited"),
            "white_time_ms": wt,
            "black_time_ms": bt,
            "duck_square":  g.get("duck_square"),
            "duck_pending": g.get("duck_pending", False),
            "check_counts": _check_counts(board),
        }

def _current_times(g):
    wt = g.get("white_time_ms", 0)
    bt = g.get("black_time_ms", 0)
    tc = TIME_CONTROLS.get(g.get("time_control", "unlimited"), TIME_CONTROLS["unlimited"])
    if tc["initial_ms"] == 0 or g.get("status") != "active":
        return wt, bt
    started = g.get("turn_started_at")
    if not started:
        return wt, bt
    elapsed_ms = int((_time.monotonic() - started) * 1000)
    if g["board"].turn == chess.WHITE:
        return max(0, wt - elapsed_ms), bt
    return wt, max(0, bt - elapsed_ms)

def _apply_move_clock(g):
    tc = TIME_CONTROLS.get(g.get("time_control", "unlimited"), TIME_CONTROLS["unlimited"])
    if tc["initial_ms"] == 0:
        return False
    started = g.get("turn_started_at")
    now = _time.monotonic()
    if started is None:
        g["turn_started_at"] = now
        return False
    elapsed_ms = int((now - started) * 1000)
    board = g["board"]
    if board.turn == chess.WHITE:
        g["white_time_ms"] -= elapsed_ms
        if g["white_time_ms"] <= 0:
            g["white_time_ms"] = 0
            return True
        g["white_time_ms"] += tc["increment_ms"]
    else:
        g["black_time_ms"] -= elapsed_ms
        if g["black_time_ms"] <= 0:
            g["black_time_ms"] = 0
            return True
        g["black_time_ms"] += tc["increment_ms"]
    g["turn_started_at"] = now
    return False

def _schedule_timeout_check(game_id):
    def worker():
        while True:
            _time.sleep(1)
            with _games_lock:
                g = _games.get(game_id)
                if not g or g.get("status") != "active":
                    return
                tc = TIME_CONTROLS.get(g.get("time_control", "unlimited"), TIME_CONTROLS["unlimited"])
                if tc["initial_ms"] == 0:
                    return
                started = g.get("turn_started_at")
                if started is None:
                    continue
                elapsed_ms = int((_time.monotonic() - started) * 1000)
                board = g["board"]
                if board.turn == chess.WHITE:
                    remaining = g["white_time_ms"] - elapsed_ms
                    loser = "white"
                else:
                    remaining = g["black_time_ms"] - elapsed_ms
                    loser = "black"
                if remaining <= 0:
                    g[f"{loser}_time_ms"] = 0
                    g["status"] = "completed"
                    result = "black_wins" if loser == "white" else "white_wins"
                    board_ref = g["board"]
                    break
            pgn = _board_to_pgn(board_ref, game_id)
            rc = _finish_game(game_id, result, pgn)
            _socketio.emit("game_over", {"result": result, "pgn": pgn, "timeout": loser, "rating_change": rc},
                           to=game_id, namespace="/chess")
            return
    threading.Thread(target=worker, daemon=True).start()

def _finish_game(game_id, result, pgn):
    rating_change = None
    with db.get_db() as conn:
        conn.execute(
            "UPDATE games SET status='completed', result=?, pgn=?, moves=?, completed_at=? WHERE id=?",
            (result, pgn, " ".join(m.uci() for m in _games[game_id]["board"].move_stack),
             datetime.utcnow().isoformat(), game_id)
        )
        rating_change = db.record_result(conn, game_id, result)

    _discord_notify(game_id, result, rating_change)

    with _games_lock:
        g = _games.get(game_id, {})
        engine = g.get("engine")
        if engine:
            try: engine.quit()
            except Exception: pass
        base_meta = {
            "result":         result,
            "variant":        g.get("variant"),
            "time_control":   g.get("time_control"),
            "white":          g.get("white"),
            "black":          g.get("black"),
            "white_is_ai":    g.get("white_is_ai"),
            "black_is_ai":    g.get("black_is_ai"),
            "bot_name":       g.get("bot_name"),
            "moves":          len(g.get("board").move_stack) if g.get("board") else 0,
            "rating_change":  rating_change,
        }
        for role, uname, is_ai in (("white", g.get("white"), g.get("white_is_ai")),
                                    ("black", g.get("black"), g.get("black_is_ai"))):
            if uname and not is_ai:
                stats_emit.emit(uname, "chess", game_id,
                                item_name=f"CHESS {g.get('variant','standard').upper()}",
                                metadata={**base_meta, "self_role": role,
                                          "won": (result == f"{role}_wins"),
                                          "drew": result == "draw"})
        _games.pop(game_id, None)

    return rating_change

def _discord_notify(game_id, result, rating_change=None):
    if not DISCORD_WEBHOOK:
        return
    with db.get_db() as conn:
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
    if rating_change:
        w = rating_change["white"]; b = rating_change["black"]
        wd = f"{'+' if w['delta']>=0 else ''}{w['delta']}"
        bd = f"{'+' if b['delta']>=0 else ''}{b['delta']}"
        label += f"  ({white} {w['new']} {wd}, {black} {b['new']} {bd})"
    payload = json.dumps({"content": f"USG ISHIMURA CHESS | {label}"}).encode()
    try:
        req = urllib.request.Request(DISCORD_WEBHOOK, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def _ai_move(game_id):
    with _games_lock:
        g = _games.get(game_id)
        if not g:
            return
        board = g["board"].copy()
        engine = g.get("engine")
        level = g.get("ai_level", 5)

    if not engine:
        try:
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception:
            return
        with _games_lock:
            g = _games.get(game_id)
            if not g:
                try: engine.quit()
                except Exception: pass
                return
            g["engine"] = engine

    try:
        conf = {"Skill Level": level}
        with _games_lock:
            g = _games.get(game_id)
            if g and g.get("variant") == "chess960":
                conf["UCI_Chess960"] = True
        engine.configure(conf)
        result = engine.play(board, chess.engine.Limit(time=0.5))
        move = result.move
    except Exception:
        return

    with _games_lock:
        g = _games.get(game_id)
        if not g or g["status"] != "active":
            return
        try:
            san = g["board"].san(move)
        except Exception:
            san = move.uci()
        g.setdefault("san_stack", []).append(san)
        g["board"].push(move)
        board = g["board"]
        if g.get("variant") == "duck":
            empty = [sq for sq in chess.SQUARES if board.piece_at(sq) is None]
            if empty:
                g["duck_square"] = random.choice(empty)
            g["duck_pending"] = False
        _touch(g)
        timeout = _apply_move_clock(g)

    if timeout:
        with _games_lock:
            g = _games.get(game_id)
            if g:
                g["status"] = "completed"
        loser = "black" if board.turn == chess.WHITE else "white"
        result = "black_wins" if loser == "white" else "white_wins"
        pgn = _board_to_pgn(board, game_id)
        rc = _finish_game(game_id, result, pgn)
        _socketio.emit("game_over", {"result": result, "pgn": pgn, "timeout": loser, "rating_change": rc},
                       to=game_id, namespace="/chess")
        return

    with db.get_db() as conn:
        conn.execute("UPDATE games SET moves=?, white_time_ms=?, black_time_ms=? WHERE id=?",
                     (" ".join(m.uci() for m in board.move_stack),
                      g.get("white_time_ms", 0), g.get("black_time_ms", 0), game_id))

    state = _board_state(game_id)
    _socketio.emit("game_state", state, to=game_id, namespace="/chess")

    with _games_lock:
        variant = _games.get(game_id, {}).get("variant", "standard")
    is_over = board.is_game_over() or (variant == "duck" and _duck_king_captured(board))
    if is_over:
        if variant == "duck" and _duck_king_captured(board):
            result = "white_wins" if board.turn == chess.BLACK else "black_wins"
        else:
            outcome = board.outcome()
            result = _outcome_to_result(outcome)
        pgn = _board_to_pgn(board, game_id)
        rc = _finish_game(game_id, result, pgn)
        _socketio.emit("game_over", {"result": result, "pgn": pgn, "rating_change": rc},
                       to=game_id, namespace="/chess")

def _outcome_to_result(outcome):
    if outcome is None:
        return "draw"
    if outcome.winner == chess.WHITE:
        return "white_wins"
    if outcome.winner == chess.BLACK:
        return "black_wins"
    return "draw"

def _board_to_pgn(board, game_id):
    pgn_game = chess.pgn.Game.from_board(board)
    with _games_lock:
        g = _games.get(game_id, {})
        variant = g.get("variant", "standard")
        if g.get("white"): pgn_game.headers["White"] = g["white"]
        if g.get("black"): pgn_game.headers["Black"] = g["black"]
        if g.get("bot_name"):
            side = "White" if g.get("white_is_ai") else "Black"
            pgn_game.headers[side] = f"Bot ({g['bot_name']})"
    tag = PGN_VARIANT_TAGS.get(variant)
    if tag:
        pgn_game.headers["Variant"] = tag
    pgn_game.headers["Site"] = "USG Ishimura Chess"
    return str(pgn_game)


bp = Blueprint("chess", __name__, template_folder="templates")

@bp.route("/")
def lobby():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        active = db.get_active_games(conn)
        leaders = db.get_leaderboard(conn)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
    return render_template("chess/lobby.html", user=user, active_games=active,
                           leaderboard=leaders, me=me,
                           bots=BOTS, variants=VARIANTS, time_controls=TIME_CONTROLS)

@bp.route("/game/new", methods=["POST"])
def new_game():
    user = get_user()
    game_type    = request.form.get("type", "human")
    color        = request.form.get("color", "white")
    bot_key      = request.form.get("bot", "officer")
    variant      = request.form.get("variant", "standard")
    time_control = request.form.get("time_control", "unlimited")
    game_id      = uuid.uuid4().hex

    if variant not in VARIANTS:           variant = "standard"
    if time_control not in TIME_CONTROLS: time_control = "unlimited"
    bot = BOTS.get(bot_key, BOTS["officer"])
    ai_level = bot["level"]

    white = black = None
    white_is_ai = black_is_ai = False
    bot_name = ""

    if game_type == "ai":
        if color == "white":
            white, black = user, None
            black_is_ai = True
        else:
            white, black = None, user
            white_is_ai = True
        status = "active"
        bot_name = bot["name"]
    else:
        if color == "white":
            white = user
        else:
            black = user
        status = "waiting"

    tc = TIME_CONTROLS[time_control]
    white_time_ms = tc["initial_ms"]
    black_time_ms = tc["initial_ms"]

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        conn.execute(
            "INSERT INTO games (id, white, black, white_is_ai, black_is_ai, ai_level, bot_name, variant, time_control, white_time_ms, black_time_ms, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (game_id, white, black, int(white_is_ai), int(black_is_ai), ai_level, bot_name,
             variant, time_control, white_time_ms, black_time_ms, status)
        )

    if variant == "chess960":
        board = chess.Board.from_chess960_pos(random.randint(0, 959))
    else:
        board = make_board(variant)

    engine = None
    if game_type == "ai":
        try:
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception:
            engine = None

    with _games_lock:
        _games[game_id] = {
            "board": board, "white": white, "black": black,
            "white_is_ai": white_is_ai, "black_is_ai": black_is_ai,
            "ai_level": ai_level, "bot_name": bot_name,
            "variant": variant, "time_control": time_control,
            "white_time_ms": white_time_ms, "black_time_ms": black_time_ms,
            "turn_started_at": _time.monotonic() if status == "active" else None,
            "last_activity": _time.monotonic(),
            "duck_square": None, "duck_pending": False, "san_stack": [],
            "engine": engine, "status": status, "draw_offered_by": None,
        }

    if status == "active" and tc["initial_ms"] > 0:
        _schedule_timeout_check(game_id)
    if game_type == "ai" and white_is_ai:
        threading.Thread(target=_ai_move, args=(game_id,), daemon=True).start()

    return redirect(url_for("chess.game", game_id=game_id))

@bp.route("/game/<game_id>")
def game(game_id):
    user = get_user()
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
    if not row:
        abort(404)

    with _games_lock:
        if game_id not in _games and row["status"] in ("waiting", "active"):
            variant = row["variant"] or "standard"
            board = make_board(variant)
            san_stack = []
            for uci in (row["moves"] or "").split():
                if uci:
                    m = chess.Move.from_uci(uci)
                    try:
                        san_stack.append(board.san(m))
                    except Exception:
                        san_stack.append(uci)
                    board.push(m)
            _games[game_id] = {
                "board": board, "white": row["white"], "black": row["black"],
                "white_is_ai": bool(row["white_is_ai"]), "black_is_ai": bool(row["black_is_ai"]),
                "ai_level": row["ai_level"], "bot_name": row["bot_name"] or "",
                "variant": variant, "time_control": row["time_control"] or "unlimited",
                "white_time_ms": row["white_time_ms"] or 0,
                "black_time_ms": row["black_time_ms"] or 0,
                "turn_started_at": _time.monotonic() if row["status"] == "active" else None,
                "last_activity": _time.monotonic(),
                "duck_square": None, "duck_pending": False, "san_stack": san_stack,
                "engine": None, "status": row["status"], "draw_offered_by": None,
            }
            if row["status"] == "active" and (row["white_time_ms"] or 0) > 0:
                _schedule_timeout_check(game_id)

    my_color = None
    if row["white"] == user:   my_color = "white"
    elif row["black"] == user: my_color = "black"

    return render_template("chess/game.html", game_id=game_id, user=user,
                           my_color=my_color, game=row)

@bp.route("/game/<game_id>/rematch", methods=["POST", "GET"])
def rematch(game_id):
    user = get_user()
    with db.get_db() as conn:
        prev = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
    if not prev:
        abort(404)

    prev_white = prev["white"]
    prev_black = prev["black"]
    was_ai = bool(prev["white_is_ai"] or prev["black_is_ai"])

    if user == prev_white:
        my_prev_color = "white"
    elif user == prev_black:
        my_prev_color = "black"
    else:
        my_prev_color = "white"

    new_color = "black" if my_prev_color == "white" else "white"

    bot_key = "officer"
    for k, b in BOTS.items():
        if b["name"] == (prev["bot_name"] or ""):
            bot_key = k
            break

    new_game_id = uuid.uuid4().hex
    white = black = None
    white_is_ai = black_is_ai = False
    bot_name = ""

    if was_ai:
        if new_color == "white":
            white, black = user, None
            black_is_ai = True
        else:
            white, black = None, user
            white_is_ai = True
        status = "active"
        bot_name = BOTS[bot_key]["name"]
    else:
        if new_color == "white":
            white = user
            if prev_white and prev_white != user: black = prev_white
            elif prev_black and prev_black != user: black = prev_black
        else:
            black = user
            if prev_white and prev_white != user: white = prev_white
            elif prev_black and prev_black != user: white = prev_black
        status = "active" if (white and black) else "waiting"

    variant = prev["variant"] or "standard"
    time_control = prev["time_control"] or "unlimited"
    tc = TIME_CONTROLS.get(time_control, TIME_CONTROLS["unlimited"])

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        conn.execute(
            "INSERT INTO games (id, white, black, white_is_ai, black_is_ai, ai_level, bot_name, variant, time_control, white_time_ms, black_time_ms, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (new_game_id, white, black, int(white_is_ai), int(black_is_ai),
             BOTS[bot_key]["level"], bot_name,
             variant, time_control, tc["initial_ms"], tc["initial_ms"], status)
        )

    if variant == "chess960":
        board = chess.Board.from_chess960_pos(random.randint(0, 959))
    else:
        board = make_board(variant)

    engine = None
    if was_ai:
        try:
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception:
            engine = None

    with _games_lock:
        _games[new_game_id] = {
            "board": board, "white": white, "black": black,
            "white_is_ai": white_is_ai, "black_is_ai": black_is_ai,
            "ai_level": BOTS[bot_key]["level"], "bot_name": bot_name,
            "variant": variant, "time_control": time_control,
            "white_time_ms": tc["initial_ms"], "black_time_ms": tc["initial_ms"],
            "turn_started_at": _time.monotonic() if status == "active" else None,
            "last_activity": _time.monotonic(),
            "duck_square": None, "duck_pending": False, "san_stack": [],
            "engine": engine, "status": status, "draw_offered_by": None,
        }

    if status == "active" and tc["initial_ms"] > 0:
        _schedule_timeout_check(new_game_id)
    if was_ai and white_is_ai:
        threading.Thread(target=_ai_move, args=(new_game_id,), daemon=True).start()

    return redirect(url_for("chess.game", game_id=new_game_id))

@bp.route("/game/<game_id>/resign", methods=["POST"])
def http_resign(game_id):
    """HTTP fallback for resign when SocketIO is down or stuck."""
    user = get_user()
    with _games_lock:
        g = _games.get(game_id)
        if not g:
            # Rehydrate from DB if evicted
            with db.get_db() as conn:
                row = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
            if not row or row["status"] == "completed":
                return jsonify({"error": "Game not active"}), 400
            if user not in (row["white"], row["black"]):
                return jsonify({"error": "Not a participant"}), 403
            with db.get_db() as conn:
                if row["status"] == "waiting":
                    conn.execute("DELETE FROM games WHERE id=?", (game_id,))
                    return jsonify({"ok": True, "cancelled": True})
                result = "black_wins" if row["white"] == user else "white_wins"
                conn.execute(
                    "UPDATE games SET status='completed', result=?, completed_at=? WHERE id=?",
                    (result, datetime.utcnow().isoformat(), game_id)
                )
                db.record_result(conn, game_id, result)
            return jsonify({"ok": True, "result": result})
        if user not in (g["white"], g["black"]):
            return jsonify({"error": "Not a participant"}), 403
        if g["status"] == "waiting":
            _games.pop(game_id, None)
            with db.get_db() as conn:
                conn.execute("DELETE FROM games WHERE id=?", (game_id,))
            return jsonify({"ok": True, "cancelled": True})
        if g["status"] != "active":
            return jsonify({"error": "Game not active"}), 400
        result = "black_wins" if g["white"] == user else "white_wins"
        g["status"] = "completed"
    board = g["board"]
    pgn = _board_to_pgn(board, game_id)
    rc = _finish_game(game_id, result, pgn)
    if _socketio:
        _socketio.emit("game_over", {"result": result, "pgn": pgn, "resigned": user, "rating_change": rc},
                       to=game_id, namespace="/chess")
    return jsonify({"ok": True, "result": result, "rating_change": rc})

@bp.route("/game/<game_id>/pgn")
def game_pgn(game_id):
    with db.get_db() as conn:
        row = conn.execute("SELECT pgn, white, black FROM games WHERE id=? AND status='completed'", (game_id,)).fetchone()
    if not row or not row["pgn"]:
        abort(404)
    filename = f"ishimura-{row['white'] or 'ai'}-vs-{row['black'] or 'ai'}-{game_id[:8]}.pgn"
    return Response(row["pgn"], mimetype="application/x-chess-pgn",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@bp.route("/analysis/<game_id>")
def analysis(game_id):
    user = get_user()
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
        existing = conn.execute(
            "SELECT * FROM game_analysis WHERE game_id=? ORDER BY move_number",
            (game_id,)
        ).fetchall()
    if not row:
        abort(404)
    return render_template("chess/analysis.html", game_id=game_id, user=user,
                           game=row, analysis=existing)

@bp.route("/api/leaderboard")
def api_leaderboard():
    with db.get_db() as conn:
        leaders = db.get_leaderboard(conn)
    return jsonify([dict(r) for r in leaders])

@bp.route("/api/fens", methods=["POST"])
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


def _run_analysis(game_id):
    with db.get_db() as conn:
        row = conn.execute("SELECT moves, variant FROM games WHERE id=?", (game_id,)).fetchone()
    if not row or not row["moves"]:
        return
    move_ucis = row["moves"].split()
    board = make_board(row["variant"] or "standard")

    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except Exception:
        _socketio.emit("analysis_error", {"message": "Stockfish unavailable"},
                       to=game_id, namespace="/chess")
        return

    try:
        with db.get_db() as conn:
            conn.execute("DELETE FROM game_analysis WHERE game_id=?", (game_id,))

        for i, uci in enumerate(move_ucis):
            info = engine.analyse(board, chess.engine.Limit(depth=15))
            score = info["score"].white()
            eval_cp = score.score(mate_score=10000) if score is not None else None
            best = info.get("pv", [None])[0]
            best_uci = best.uci() if best else None

            with db.get_db() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO game_analysis (game_id, move_number, move_uci, evaluation, best_move) VALUES (?,?,?,?,?)",
                    (game_id, i, uci, eval_cp, best_uci)
                )

            _socketio.emit("analysis_update", {
                "move_number": i, "move_uci": uci,
                "evaluation":  eval_cp, "best_move": best_uci,
            }, to=game_id, namespace="/chess")

            board.push(chess.Move.from_uci(uci))

        _socketio.emit("analysis_complete", {}, to=game_id, namespace="/chess")
    finally:
        engine.quit()


def register_sockets(socketio):
    global _socketio
    _socketio = socketio

    @socketio.on("join_game", namespace="/chess")
    def on_join(data):
        game_id = data.get("game_id")
        user = get_user()
        if not game_id:
            return
        join_room(game_id)

        with _games_lock:
            g = _games.get(game_id)
            if not g:
                return
            _touch(g)
            just_activated = False
            if g["status"] == "waiting" and user not in (g["white"], g["black"]):
                if g["white"] is None:   g["white"] = user
                elif g["black"] is None: g["black"] = user
                g["status"] = "active"
                g["turn_started_at"] = _time.monotonic()
                just_activated = True
                with db.get_db() as conn:
                    db.ensure_user(conn, user)
                    conn.execute(
                        "UPDATE games SET white=?, black=?, status='active' WHERE id=?",
                        (g["white"], g["black"], game_id)
                    )

        if just_activated:
            tc = TIME_CONTROLS.get(g.get("time_control", "unlimited"), TIME_CONTROLS["unlimited"])
            if tc["initial_ms"] > 0:
                _schedule_timeout_check(game_id)

        my_color = None
        with _games_lock:
            g = _games.get(game_id)
            if g:
                if g["white"] == user:   my_color = "white"
                elif g["black"] == user: my_color = "black"
        emit("your_color", {"color": my_color})

        state = _board_state(game_id)
        emit("game_state", state, to=game_id)

        ai_to_move = False
        with _games_lock:
            g = _games.get(game_id)
            if g and g.get("status") == "active" and not g.get("duck_pending"):
                board = g["board"]
                ai_to_move = (board.turn == chess.WHITE and g["white_is_ai"]) or \
                             (board.turn == chess.BLACK and g["black_is_ai"])
        if ai_to_move:
            threading.Thread(target=_ai_move, args=(game_id,), daemon=True).start()

    @socketio.on("make_move", namespace="/chess")
    def on_move(data):
        game_id = data.get("game_id")
        move_uci = data.get("move")
        promotion = data.get("promotion", "q")
        user = get_user()

        with _games_lock:
            g = _games.get(game_id)
            if not g or g["status"] != "active":
                emit("error", {"message": "Game not active"})
                return
            board = g["board"]
            if board.turn == chess.WHITE and g["white"] != user:
                emit("error", {"message": "Not your turn"}); return
            if board.turn == chess.BLACK and g["black"] != user:
                emit("error", {"message": "Not your turn"}); return

            try:
                if len(move_uci) == 4:
                    from_sq = chess.parse_square(move_uci[:2])
                    to_sq   = chess.parse_square(move_uci[2:])
                    piece   = board.piece_at(from_sq)
                    if piece and piece.piece_type == chess.PAWN:
                        rank = chess.square_rank(to_sq)
                        if rank in (0, 7):
                            move_uci += promotion
                move = chess.Move.from_uci(move_uci)
                if g.get("variant") == "duck":
                    if not _duck_move_legal(board, move, g.get("duck_square")):
                        emit("error", {"message": "Illegal move"}); return
                elif move not in board.legal_moves:
                    emit("error", {"message": "Illegal move"}); return
                try:
                    san = board.san(move)
                except Exception:
                    san = move.uci()
                g.setdefault("san_stack", []).append(san)
                board.push(move)
                _touch(g)
            except Exception:
                emit("error", {"message": "Invalid move"}); return

            if _apply_move_clock(g):
                g["status"] = "completed"
                loser = "black" if board.turn == chess.WHITE else "white"
                result = "black_wins" if loser == "white" else "white_wins"
                pgn = _board_to_pgn(board, game_id)
                rc = _finish_game(game_id, result, pgn)
                emit("game_over", {"result": result, "pgn": pgn, "timeout": loser, "rating_change": rc},
                     to=game_id)
                return

            if g.get("variant") == "duck":
                g["duck_pending"] = True

            ai_to_move = (board.turn == chess.WHITE and g["white_is_ai"]) or \
                         (board.turn == chess.BLACK and g["black_is_ai"])
            is_over = board.is_game_over() or (g.get("variant") == "duck" and _duck_king_captured(board))

        with db.get_db() as conn:
            conn.execute("UPDATE games SET moves=?, white_time_ms=?, black_time_ms=? WHERE id=?",
                         (" ".join(m.uci() for m in board.move_stack),
                          g.get("white_time_ms", 0), g.get("black_time_ms", 0), game_id))

        state = _board_state(game_id)
        emit("game_state", state, to=game_id)

        if is_over:
            if g.get("variant") == "duck" and _duck_king_captured(board):
                result = "white_wins" if board.turn == chess.BLACK else "black_wins"
            else:
                outcome = board.outcome()
                result = _outcome_to_result(outcome)
            pgn = _board_to_pgn(board, game_id)
            rc = _finish_game(game_id, result, pgn)
            emit("game_over", {"result": result, "pgn": pgn, "rating_change": rc}, to=game_id)
        elif ai_to_move and not g.get("duck_pending"):
            threading.Thread(target=_ai_move, args=(game_id,), daemon=True).start()

    @socketio.on("place_duck", namespace="/chess")
    def on_place_duck(data):
        game_id = data.get("game_id")
        square_name = data.get("square", "")
        user = get_user()
        try:
            target = chess.parse_square(square_name)
        except Exception:
            emit("error", {"message": "Bad square"}); return

        with _games_lock:
            g = _games.get(game_id)
            if not g or g["status"] != "active" or g.get("variant") != "duck":
                return
            if not g.get("duck_pending"):
                return
            board = g["board"]
            placer_color = chess.BLACK if board.turn == chess.WHITE else chess.WHITE
            expected_user = g["white"] if placer_color == chess.WHITE else g["black"]
            is_ai = g["white_is_ai"] if placer_color == chess.WHITE else g["black_is_ai"]
            if not is_ai and expected_user != user:
                emit("error", {"message": "Not your duck"}); return
            if board.piece_at(target) is not None:
                emit("error", {"message": "Square occupied"}); return
            g["duck_square"] = target
            g["duck_pending"] = False
            _touch(g)
            ai_to_move = (board.turn == chess.WHITE and g["white_is_ai"]) or \
                         (board.turn == chess.BLACK and g["black_is_ai"])

        state = _board_state(game_id)
        emit("game_state", state, to=game_id)
        if ai_to_move:
            threading.Thread(target=_ai_move, args=(game_id,), daemon=True).start()

    @socketio.on("resign", namespace="/chess")
    def on_resign(data):
        game_id = data.get("game_id")
        user = get_user()
        with _games_lock:
            g = _games.get(game_id)
            if not g:
                return
            if g["status"] == "waiting":
                if user not in (g["white"], g["black"]):
                    return
                _games.pop(game_id, None)
                with db.get_db() as conn:
                    conn.execute("DELETE FROM games WHERE id=?", (game_id,))
                emit("game_over", {"result": "cancelled", "pgn": "", "resigned": user}, to=game_id)
                return
            if g["status"] != "active":
                return
            result = "black_wins" if g["white"] == user else "white_wins"
            g["status"] = "completed"

        board = g["board"]
        pgn = _board_to_pgn(board, game_id)
        rc = _finish_game(game_id, result, pgn)
        emit("game_over", {"result": result, "pgn": pgn, "resigned": user, "rating_change": rc}, to=game_id)

    @socketio.on("offer_draw", namespace="/chess")
    def on_offer_draw(data):
        game_id = data.get("game_id")
        user = get_user()
        with _games_lock:
            g = _games.get(game_id)
            if not g or g["status"] != "active":
                return
            # Opponent is a bot - bots don't accept draws
            opponent_is_ai = (g["white_is_ai"] if g["black"] == user else g["black_is_ai"])
            if opponent_is_ai:
                emit("draw_declined", {"by": g.get("bot_name") or "BOT", "reason": "The bot never accepts a draw"})
                return
            g["draw_offered_by"] = user
        emit("draw_offered", {"by": user}, to=game_id)

    @socketio.on("accept_draw", namespace="/chess")
    def on_accept_draw(data):
        game_id = data.get("game_id")
        user = get_user()
        with _games_lock:
            g = _games.get(game_id)
            if not g or g["status"] != "active" or g["draw_offered_by"] == user:
                return
            g["status"] = "completed"
        board = g["board"]
        pgn = _board_to_pgn(board, game_id)
        rc = _finish_game(game_id, "draw", pgn)
        emit("game_over", {"result": "draw", "pgn": pgn, "rating_change": rc}, to=game_id)

    @socketio.on("request_analysis", namespace="/chess")
    def on_request_analysis(data):
        game_id = data.get("game_id")
        threading.Thread(target=_run_analysis, args=(game_id,), daemon=True).start()
