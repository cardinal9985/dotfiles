import random

from flask import Blueprint, render_template, request, jsonify

import db
from shared_auth import get_user

MIN_BET = 5
MAX_BET = 2000

PAYOUT_OVER  = 1  # 1:1
PAYOUT_UNDER = 1  # 1:1
PAYOUT_EQUAL = 4  # 4:1

bp = Blueprint("dice", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        recent = conn.execute(
            "SELECT * FROM dice_rolls WHERE username=? ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
    return render_template("dice/table.html", user=user, me=me, recent=recent,
                           min_bet=MIN_BET, max_bet=MAX_BET,
                           payout_over=PAYOUT_OVER, payout_under=PAYOUT_UNDER,
                           payout_equal=PAYOUT_EQUAL)

@bp.route("/api/roll", methods=["POST"])
def api_roll():
    user = get_user()
    try:
        b_over  = int(request.json.get("bet_over",  0))
        b_under = int(request.json.get("bet_under", 0))
        b_equal = int(request.json.get("bet_equal", 0))
    except Exception:
        return jsonify({"error": "Bad bet"}), 400
    total_bet = b_over + b_under + b_equal
    if total_bet < MIN_BET:
        return jsonify({"error": f"Min total bet {MIN_BET}"}), 400
    for b in (b_over, b_under, b_equal):
        if b < 0 or b > MAX_BET:
            return jsonify({"error": f"Each bet 0-{MAX_BET}"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < total_bet:
            return jsonify({"error": "Not enough chips"}), 400
        db.adjust_chips(conn, user, -total_bet, "dice_bet")

    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    total = d1 + d2

    payout = 0
    if total > 7 and b_over > 0:
        payout += b_over * (PAYOUT_OVER + 1)
    if total < 7 and b_under > 0:
        payout += b_under * (PAYOUT_UNDER + 1)
    if total == 7 and b_equal > 0:
        payout += b_equal * (PAYOUT_EQUAL + 1)

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "dice_win")
        conn.execute(
            "INSERT INTO dice_rolls (username, bet_over, bet_under, bet_equal, d1, d2, total, payout) VALUES (?,?,?,?,?,?,?,?)",
            (user, b_over, b_under, b_equal, d1, d2, total, payout)
        )
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    return jsonify({
        "d1": d1, "d2": d2, "total": total,
        "payout": payout, "total_bet": total_bet,
        "net": payout - total_bet,
        "new_balance": new_balance,
    })
