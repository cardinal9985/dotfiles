from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

ENTRY_FEE = 20
PAYOUT_PER_HIT = 3   # ~7 hits break even, 15+ solid win
ROUND_SECS = 30
MAX_HITS = 60        # sanity cap

bp = Blueprint("whack", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        best = conn.execute(
            "SELECT MAX(hits) as best FROM whack_rounds WHERE username=?", (user,)
        ).fetchone()["best"]
        leaderboard = conn.execute("""
            SELECT username, MAX(hits) as best_hits, COUNT(*) as rounds
            FROM whack_rounds
            GROUP BY username
            ORDER BY best_hits DESC
            LIMIT 10
        """).fetchall()
        recent = conn.execute(
            "SELECT * FROM whack_rounds WHERE username=? ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
    return render_template("whack/table.html", user=user, me=me, best=best,
                           leaderboard=leaderboard, recent=recent,
                           entry_fee=ENTRY_FEE, payout_per_hit=PAYOUT_PER_HIT,
                           round_secs=ROUND_SECS)

@bp.route("/api/finish", methods=["POST"])
def api_finish():
    user = get_user()
    try:
        hits = int(request.json.get("hits", 0))
        misses = int(request.json.get("misses", 0))
    except Exception:
        return jsonify({"error": "Bad payload"}), 400
    if hits < 0 or hits > MAX_HITS or misses < 0 or misses > 200:
        return jsonify({"error": "Out of range"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ENTRY_FEE:
            return jsonify({"error": f"Need {ENTRY_FEE} tickets"}), 400
        db.adjust_chips(conn, user, -ENTRY_FEE, "whack_entry")

    payout = hits * PAYOUT_PER_HIT

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "whack_payout")
        cur = conn.execute(
            "INSERT INTO whack_rounds (username, hits, misses, entry_fee, payout) VALUES (?,?,?,?,?)",
            (user, hits, misses, ENTRY_FEE, payout)
        )
        round_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "whack", round_id, item_name="WHACK-A-MOLE", metadata={
        "hits": hits, "misses": misses, "payout": payout, "net": payout - ENTRY_FEE,
    })

    return jsonify({
        "hits":        hits,
        "misses":      misses,
        "payout":      payout,
        "net":         payout - ENTRY_FEE,
        "new_balance": new_balance,
    })
