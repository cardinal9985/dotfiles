from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

ENTRY_FEE = 15
POINTS_PER_POP = 2
GOLD_POP_BONUS = 20   # extra tickets on a gold pop
MAX_POPS = 100

bp = Blueprint("balloonpop", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        best = conn.execute(
            "SELECT MAX(pops) as best FROM balloonpop_rounds WHERE username=?", (user,)
        ).fetchone()["best"]
        leaderboard = conn.execute("""
            SELECT username, MAX(pops) as best_pops, SUM(gold_pops) as golds, COUNT(*) as rounds
            FROM balloonpop_rounds
            GROUP BY username
            ORDER BY best_pops DESC
            LIMIT 10
        """).fetchall()
    return render_template("balloonpop/table.html", user=user, me=me,
                           best=best, leaderboard=leaderboard,
                           entry_fee=ENTRY_FEE, points_per_pop=POINTS_PER_POP,
                           gold_bonus=GOLD_POP_BONUS)

@bp.route("/api/finish", methods=["POST"])
def api_finish():
    user = get_user()
    try:
        pops = int(request.json.get("pops", 0))
        gold_pops = int(request.json.get("gold_pops", 0))
    except Exception:
        return jsonify({"error": "Bad payload"}), 400
    if pops < 0 or pops > MAX_POPS or gold_pops < 0 or gold_pops > pops:
        return jsonify({"error": "Out of range"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ENTRY_FEE:
            return jsonify({"error": f"Need {ENTRY_FEE} tickets"}), 400
        db.adjust_chips(conn, user, -ENTRY_FEE, "balloonpop_entry")

    payout = pops * POINTS_PER_POP + gold_pops * GOLD_POP_BONUS

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "balloonpop_payout")
        cur = conn.execute(
            "INSERT INTO balloonpop_rounds (username, pops, gold_pops, entry_fee, payout) VALUES (?,?,?,?,?)",
            (user, pops, gold_pops, ENTRY_FEE, payout)
        )
        round_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "balloonpop", round_id, item_name="BALLOON POP", metadata={
        "pops": pops, "gold_pops": gold_pops, "payout": payout, "net": payout - ENTRY_FEE,
    })

    return jsonify({
        "pops": pops, "gold_pops": gold_pops, "payout": payout,
        "net": payout - ENTRY_FEE, "new_balance": new_balance,
    })
