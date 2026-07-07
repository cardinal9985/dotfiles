import os

from flask import Flask, render_template, redirect, url_for, abort
from flask_socketio import SocketIO

import db
from shared_auth import get_user

DB_PATH = os.environ.get("GAMES_DB_PATH", "/tmp/games.db")
db.DB_PATH = DB_PATH

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ishimura-games-dev")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

@app.before_request
def require_auth():
    from flask import request
    if request.path == "/health":
        return None
    if request.path.startswith("/api/user/") and request.remote_addr in ("127.0.0.1", "::1"):
        return None
    if not get_user() and not app.debug:
        return "Unauthorized", 401

@app.route("/health")
def health():
    return "ok", 200

@app.route("/api/user/<username>/dossier")
def user_dossier(username):
    from flask import jsonify
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        games_played = conn.execute(
            "SELECT COUNT(*) as c FROM games WHERE (white=? OR black=?) AND status='completed'",
            (username, username)
        ).fetchone()["c"]
        bj_hands = conn.execute(
            "SELECT COUNT(*) as c FROM blackjack_hands WHERE username=?",
            (username,)
        ).fetchone()["c"]
        slot_spins = conn.execute(
            "SELECT COUNT(*) as c FROM slot_spins WHERE username=?",
            (username,)
        ).fetchone()["c"]
        arbiter_calls = conn.execute(
            "SELECT COUNT(*) as c FROM arbiter_calls WHERE winner=?",
            (username,)
        ).fetchone()["c"]
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "username":            row["username"],
        "member_since":        (row["created_at"] or "")[:10],
        "chess_rating":        row["rating"],
        "chess_wins":          row["wins"],
        "chess_losses":        row["losses"],
        "chess_draws":         row["draws"],
        "chess_games_played":  games_played,
        "tickets":             row["chips"],
        "tickets_lifetime_won": row["chips_lifetime_won"],
        "blackjack_hands":     bj_hands,
        "slot_spins":          slot_spins,
        "arbiter_wins":        arbiter_calls,
    })

@app.route("/")
def hub():
    from flask import request as _req
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
    stipend_eligible, stipend_next, stipend_seconds = _stipend_state(user)
    stipend_claimed = _req.args.get("stipend_claimed")
    return render_template("hub.html", user=user, me=me,
                           stipend_eligible=stipend_eligible,
                           stipend_next=stipend_next,
                           stipend_seconds=stipend_seconds,
                           stipend_amount=STIPEND_AMOUNT,
                           stipend_claimed=stipend_claimed)

MIN_TIP = 1
MAX_TIP = 10000

STIPEND_AMOUNT   = 500
STIPEND_INTERVAL_DAYS = 7

def _stipend_state(username):
    """Return (eligible: bool, next_at_iso: str_or_none, seconds_remaining: int)"""
    from datetime import datetime, timedelta
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT last_stipend_at FROM users WHERE username=?", (username,)
        ).fetchone()
    last = row["last_stipend_at"] if row else None
    if not last:
        return True, None, 0
    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return True, None, 0
    next_dt = last_dt + timedelta(days=STIPEND_INTERVAL_DAYS)
    now = datetime.utcnow()
    if now >= next_dt:
        return True, None, 0
    return False, next_dt.isoformat(), int((next_dt - now).total_seconds())

@app.route("/profile/<username>")
def profile(username):
    user = get_user()
    with db.get_db() as conn:
        stats = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        games = db.get_user_games(conn, username)
        my_row = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
    if not stats:
        abort(404)
    my_chips = my_row["chips"] if my_row else 0
    from flask import request as _req
    tipped = _req.args.get("tipped")
    return render_template("profile.html", user=user, subject=username, stats=stats,
                           games=games, my_chips=my_chips,
                           min_tip=MIN_TIP, max_tip=MAX_TIP, tipped=tipped)

@app.route("/stipend/claim", methods=["POST"])
def claim_stipend():
    from datetime import datetime
    user = get_user()
    if not user:
        abort(401)
    eligible, next_at, _seconds = _stipend_state(user)
    if not eligible:
        return redirect(url_for("hub"))
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        db.adjust_chips(conn, user, STIPEND_AMOUNT, "weekly_stipend")
        conn.execute(
            "UPDATE users SET last_stipend_at=? WHERE username=?",
            (datetime.utcnow().isoformat(), user)
        )
    return redirect(url_for("hub", stipend_claimed=STIPEND_AMOUNT))

@app.route("/profile/<username>/tip", methods=["POST"])
def tip(username):
    from flask import request as _req, jsonify
    sender = get_user()
    if sender == username:
        return jsonify({"error": "You can't tip yourself"}), 400
    try:
        amount = int(_req.form.get("amount", 0))
    except Exception:
        return jsonify({"error": "Bad amount"}), 400
    if amount < MIN_TIP or amount > MAX_TIP:
        return jsonify({"error": f"Amount must be {MIN_TIP}-{MAX_TIP}"}), 400
    with db.get_db() as conn:
        recipient = conn.execute("SELECT username FROM users WHERE username=?", (username,)).fetchone()
        if not recipient:
            return jsonify({"error": "Recipient not found"}), 404
        me = conn.execute("SELECT chips FROM users WHERE username=?", (sender,)).fetchone()
        if not me or me["chips"] < amount:
            return jsonify({"error": "Not enough tickets"}), 400
        db.adjust_chips(conn, sender, -amount, f"tip_to_{username}")
        db.adjust_chips(conn, username, amount, f"tip_from_{sender}")
    return redirect(url_for("profile", username=username, tipped=amount))

@app.route("/leaderboard")
def leaderboard():
    user = get_user()
    with db.get_db() as conn:
        chess_lb   = db.get_leaderboard(conn)
        chip_lb    = db.get_chip_leaderboard(conn)
        arbiter_lb = db.get_arbiter_ledger(conn)
    return render_template("leaderboard.html", user=user, chess_lb=chess_lb,
                           chip_lb=chip_lb, arbiter_lb=arbiter_lb)

import chess_bp
app.register_blueprint(chess_bp.bp, url_prefix="/chess")
chess_bp.register_sockets(socketio)

import blackjack_bp
app.register_blueprint(blackjack_bp.bp, url_prefix="/blackjack")

import war_bp
app.register_blueprint(war_bp.bp, url_prefix="/war")
war_bp.register_sockets(socketio)

import slots_bp
app.register_blueprint(slots_bp.bp, url_prefix="/slots")

import baccarat_bp
app.register_blueprint(baccarat_bp.bp, url_prefix="/baccarat")

import dice_bp
app.register_blueprint(dice_bp.bp, url_prefix="/dice")

import roulette_bp
app.register_blueprint(roulette_bp.bp, url_prefix="/roulette")

import connect4_bp
app.register_blueprint(connect4_bp.bp, url_prefix="/connect4")
connect4_bp.register_sockets(socketio)

import reaction_bp
app.register_blueprint(reaction_bp.bp, url_prefix="/reaction")

import duckrace_bp
app.register_blueprint(duckrace_bp.bp, url_prefix="/duckrace")
duckrace_bp.register_sockets(socketio)

import yahtzee_bp
app.register_blueprint(yahtzee_bp.bp, url_prefix="/yahtzee")

import whack_bp
app.register_blueprint(whack_bp.bp, url_prefix="/whack")

import snake_bp
app.register_blueprint(snake_bp.bp, url_prefix="/snake")

import highstriker_bp
app.register_blueprint(highstriker_bp.bp, url_prefix="/highstriker")

import ringtoss_bp
app.register_blueprint(ringtoss_bp.bp, url_prefix="/ringtoss")

import balloonpop_bp
app.register_blueprint(balloonpop_bp.bp, url_prefix="/balloonpop")

import skeeball_bp
app.register_blueprint(skeeball_bp.bp, url_prefix="/skeeball")

import wordle_bp
app.register_blueprint(wordle_bp.bp, url_prefix="/wordle")

import tictactoe_bp
app.register_blueprint(tictactoe_bp.bp, url_prefix="/tictactoe")

if __name__ == "__main__":
    db.init_db()
    socketio.run(app, host="0.0.0.0", port=5001, debug=False, allow_unsafe_werkzeug=True)
