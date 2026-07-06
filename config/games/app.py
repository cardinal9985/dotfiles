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
    if not get_user() and not app.debug:
        return "Unauthorized", 401

@app.route("/health")
def health():
    return "ok", 200

@app.route("/")
def hub():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
    return render_template("hub.html", user=user, me=me)

@app.route("/profile/<username>")
def profile(username):
    user = get_user()
    with db.get_db() as conn:
        stats = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        games = db.get_user_games(conn, username)
    if not stats:
        abort(404)
    return render_template("profile.html", user=user, subject=username, stats=stats, games=games)

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

if __name__ == "__main__":
    db.init_db()
    socketio.run(app, host="0.0.0.0", port=5001, debug=False, allow_unsafe_werkzeug=True)
