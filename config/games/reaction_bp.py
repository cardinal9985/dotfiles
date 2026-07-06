from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

ENTRY_FEE = 10

# Payout brackets: (max_ms, payout_multiplier vs entry fee)
# Human physical limit is ~150ms; anything under 200 is suspicious
def _payout_for_time(time_ms):
    if time_ms < 200:  return ENTRY_FEE * 10   # 100 tickets - suspicious but possible
    if time_ms < 275:  return ENTRY_FEE * 5    # 50 tickets - excellent
    if time_ms < 350:  return ENTRY_FEE * 2    # 20 tickets - great
    if time_ms < 450:  return ENTRY_FEE         # 10 tickets - break even
    return 0                                    # slow - lose entry

bp = Blueprint("reaction", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        my_best = conn.execute(
            "SELECT MIN(time_ms) as best FROM reaction_attempts WHERE username=?",
            (user,)
        ).fetchone()["best"]
        recent = conn.execute(
            "SELECT * FROM reaction_attempts WHERE username=? ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
        leaderboard = conn.execute("""
            SELECT username, MIN(time_ms) as best_ms, COUNT(*) as attempts
            FROM reaction_attempts
            GROUP BY username
            ORDER BY best_ms ASC
            LIMIT 10
        """).fetchall()
    return render_template("reaction/table.html", user=user, me=me, my_best=my_best,
                           recent=recent, leaderboard=leaderboard, entry_fee=ENTRY_FEE)

@bp.route("/api/attempt", methods=["POST"])
def api_attempt():
    user = get_user()
    try:
        time_ms = int(request.json.get("time_ms", -1))
    except Exception:
        return jsonify({"error": "Bad time"}), 400
    if time_ms < 0 or time_ms > 10000:
        return jsonify({"error": "Time out of range"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ENTRY_FEE:
            return jsonify({"error": f"Need {ENTRY_FEE} tickets"}), 400
        db.adjust_chips(conn, user, -ENTRY_FEE, "reaction_entry")

    payout = _payout_for_time(time_ms)

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "reaction_payout")
        cur = conn.execute(
            "INSERT INTO reaction_attempts (username, wager, time_ms, payout) VALUES (?, ?, ?, ?)",
            (user, ENTRY_FEE, time_ms, payout)
        )
        attempt_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "reaction", attempt_id, item_name="REACTION TIME", metadata={
        "time_ms": time_ms,
        "payout":  payout,
        "net":     payout - ENTRY_FEE,
    })

    return jsonify({
        "time_ms":     time_ms,
        "payout":      payout,
        "net":         payout - ENTRY_FEE,
        "new_balance": new_balance,
    })
