from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

ENTRY_FEE = 15

# Payout brackets based on final power (0-100). Bell rings at 95+.
def _payout(power):
    if power >= 95: return 200   # BELL - jackpot
    if power >= 80: return 60    # MIGHTY
    if power >= 60: return 25    # STRONG
    if power >= 40: return 10    # OKAY (break even nearly)
    return 0                      # WEAK

bp = Blueprint("highstriker", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        best = conn.execute(
            "SELECT MAX(power) as best FROM highstriker_attempts WHERE username=?", (user,)
        ).fetchone()["best"]
        bells = conn.execute(
            "SELECT COUNT(*) as bells FROM highstriker_attempts WHERE username=? AND rang_bell=1", (user,)
        ).fetchone()["bells"]
        leaderboard = conn.execute("""
            SELECT username, MAX(power) as best_power,
                   SUM(rang_bell) as total_bells, COUNT(*) as attempts
            FROM highstriker_attempts
            GROUP BY username
            ORDER BY total_bells DESC, best_power DESC
            LIMIT 10
        """).fetchall()
    return render_template("highstriker/table.html", user=user, me=me,
                           best=best, bells=bells, leaderboard=leaderboard,
                           entry_fee=ENTRY_FEE)

@bp.route("/api/swing", methods=["POST"])
def api_swing():
    user = get_user()
    try:
        power = int(request.json.get("power", 0))
    except Exception:
        return jsonify({"error": "Bad power"}), 400
    if power < 0 or power > 100:
        return jsonify({"error": "Out of range"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ENTRY_FEE:
            return jsonify({"error": f"Need {ENTRY_FEE} tickets"}), 400
        db.adjust_chips(conn, user, -ENTRY_FEE, "highstriker_entry")

    payout = _payout(power)
    rang_bell = 1 if power >= 95 else 0

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "highstriker_payout")
        cur = conn.execute(
            "INSERT INTO highstriker_attempts (username, power, entry_fee, payout, rang_bell) VALUES (?,?,?,?,?)",
            (user, power, ENTRY_FEE, payout, rang_bell)
        )
        attempt_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "highstriker", attempt_id, item_name="HIGH STRIKER", metadata={
        "power": power, "payout": payout, "rang_bell": bool(rang_bell), "net": payout - ENTRY_FEE,
    })

    return jsonify({
        "power": power, "payout": payout, "rang_bell": bool(rang_bell),
        "net": payout - ENTRY_FEE, "new_balance": new_balance,
    })
