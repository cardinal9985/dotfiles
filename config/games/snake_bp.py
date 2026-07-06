from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

ENTRY_FEE = 10
POINTS_PER_TICKET = 5   # 5 score = 1 ticket

bp = Blueprint("snake", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        best = conn.execute(
            "SELECT MAX(score) as best FROM snake_runs WHERE username=?", (user,)
        ).fetchone()["best"]
        leaderboard = conn.execute("""
            SELECT username, MAX(score) as best_score, COUNT(*) as runs
            FROM snake_runs
            GROUP BY username
            ORDER BY best_score DESC
            LIMIT 10
        """).fetchall()
        recent = conn.execute(
            "SELECT * FROM snake_runs WHERE username=? ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
    return render_template("snake/table.html", user=user, me=me, best=best,
                           leaderboard=leaderboard, recent=recent,
                           entry_fee=ENTRY_FEE, points_per_ticket=POINTS_PER_TICKET)

@bp.route("/api/finish", methods=["POST"])
def api_finish():
    user = get_user()
    try:
        score = int(request.json.get("score", 0))
        length = int(request.json.get("length", 0))
    except Exception:
        return jsonify({"error": "Bad payload"}), 400
    if score < 0 or score > 10000 or length < 0 or length > 400:
        return jsonify({"error": "Out of range"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ENTRY_FEE:
            return jsonify({"error": f"Need {ENTRY_FEE} tickets"}), 400
        db.adjust_chips(conn, user, -ENTRY_FEE, "snake_entry")

    payout = score // POINTS_PER_TICKET

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "snake_payout")
        cur = conn.execute(
            "INSERT INTO snake_runs (username, score, length, entry_fee, payout) VALUES (?,?,?,?,?)",
            (user, score, length, ENTRY_FEE, payout)
        )
        run_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "snake", run_id, item_name="SNAKE", metadata={
        "score": score, "length": length, "payout": payout, "net": payout - ENTRY_FEE,
    })

    return jsonify({
        "score":       score,
        "length":      length,
        "payout":      payout,
        "net":         payout - ENTRY_FEE,
        "new_balance": new_balance,
    })
