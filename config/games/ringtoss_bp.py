from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

ENTRY_FEE = 10

# Peg layout: (center_pct, hit_width_pct, payout)
# Peg near center = wide + low payout; edges = narrow + high payout
PEGS = [
    {"center": 15,  "width": 12, "payout": 10},   # WIDE left
    {"center": 32,  "width": 8,  "payout": 25},
    {"center": 50,  "width": 5,  "payout": 60},   # NARROW center
    {"center": 68,  "width": 8,  "payout": 25},
    {"center": 85,  "width": 12, "payout": 10},
]

def _resolve(aim_pct):
    for i, peg in enumerate(PEGS):
        lo = peg["center"] - peg["width"] / 2
        hi = peg["center"] + peg["width"] / 2
        if lo <= aim_pct <= hi:
            return i, peg["payout"]
    return -1, 0

bp = Blueprint("ringtoss", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        best = conn.execute(
            "SELECT MAX(payout) as best FROM ringtoss_rounds WHERE username=?", (user,)
        ).fetchone()["best"]
        leaderboard = conn.execute("""
            SELECT username, SUM(rings_won) as rings, MAX(payout) as best_payout, COUNT(*) as attempts
            FROM ringtoss_rounds
            GROUP BY username
            ORDER BY rings DESC
            LIMIT 10
        """).fetchall()
    return render_template("ringtoss/table.html", user=user, me=me,
                           best=best, leaderboard=leaderboard,
                           entry_fee=ENTRY_FEE, pegs=PEGS)

@bp.route("/api/throw", methods=["POST"])
def api_throw():
    user = get_user()
    try:
        aim = float(request.json.get("aim", -1))
    except Exception:
        return jsonify({"error": "Bad aim"}), 400
    if aim < 0 or aim > 100:
        return jsonify({"error": "Aim out of range"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ENTRY_FEE:
            return jsonify({"error": f"Need {ENTRY_FEE} tickets"}), 400
        db.adjust_chips(conn, user, -ENTRY_FEE, "ringtoss_entry")

    peg_idx, payout = _resolve(aim)

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "ringtoss_payout")
        cur = conn.execute(
            "INSERT INTO ringtoss_rounds (username, rings_won, entry_fee, payout) VALUES (?,?,?,?)",
            (user, 1 if peg_idx >= 0 else 0, ENTRY_FEE, payout)
        )
        round_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "ringtoss", round_id, item_name="RING TOSS", metadata={
        "aim": aim, "peg_idx": peg_idx, "payout": payout, "net": payout - ENTRY_FEE,
    })

    return jsonify({
        "aim": aim, "peg_idx": peg_idx, "payout": payout,
        "net": payout - ENTRY_FEE, "new_balance": new_balance,
    })
