from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

ENTRY_FEE = 20
BALLS_PER_ROUND = 9
POINTS_PER_TICKET = 20   # ~180 score break even, 300+ solid win

bp = Blueprint("skeeball", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        best = conn.execute(
            "SELECT MAX(score) as best FROM skeeball_rounds WHERE username=?", (user,)
        ).fetchone()["best"]
        leaderboard = conn.execute("""
            SELECT username, MAX(score) as best_score, COUNT(*) as rounds
            FROM skeeball_rounds
            GROUP BY username
            ORDER BY best_score DESC
            LIMIT 10
        """).fetchall()
    return render_template("skeeball/table.html", user=user, me=me,
                           best=best, leaderboard=leaderboard,
                           entry_fee=ENTRY_FEE, balls_per_round=BALLS_PER_ROUND,
                           points_per_ticket=POINTS_PER_TICKET)

@bp.route("/api/finish", methods=["POST"])
def api_finish():
    user = get_user()
    try:
        score = int(request.json.get("score", 0))
    except Exception:
        return jsonify({"error": "Bad payload"}), 400
    max_possible = BALLS_PER_ROUND * 100
    if score < 0 or score > max_possible:
        return jsonify({"error": "Out of range"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ENTRY_FEE:
            return jsonify({"error": f"Need {ENTRY_FEE} tickets"}), 400
        db.adjust_chips(conn, user, -ENTRY_FEE, "skeeball_entry")

    payout = score // POINTS_PER_TICKET

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "skeeball_payout")
        cur = conn.execute(
            "INSERT INTO skeeball_rounds (username, score, entry_fee, payout) VALUES (?,?,?,?)",
            (user, score, ENTRY_FEE, payout)
        )
        round_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "skeeball", round_id, item_name="SKEE-BALL", metadata={
        "score": score, "payout": payout, "net": payout - ENTRY_FEE,
    })

    return jsonify({
        "score": score, "payout": payout,
        "net": payout - ENTRY_FEE, "new_balance": new_balance,
    })
