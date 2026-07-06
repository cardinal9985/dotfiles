import json
import random

from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

MIN_BET = 5
MAX_BET_PER_SPOT = 2000

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

PAYOUTS = {
    "straight": 35,   # single number
    "red":      1,
    "black":    1,
    "odd":      1,
    "even":     1,
    "low":      1,    # 1-18
    "high":     1,    # 19-36
    "dozen1":   2,    # 1-12
    "dozen2":   2,    # 13-24
    "dozen3":   2,    # 25-36
    "col1":     2,    # first column (bottom row: 1,4,7,...34)
    "col2":     2,
    "col3":     2,
}

def _color_of(n):
    if n == 0: return "green"
    return "red" if n in RED_NUMBERS else "black"

def _resolve_bet(kind, target, result):
    """Return True if this bet wins for the given result."""
    if result == 0:
        return kind == "straight" and target == 0
    if kind == "straight":
        return target == result
    if kind == "red":    return result in RED_NUMBERS
    if kind == "black":  return result in BLACK_NUMBERS
    if kind == "odd":    return result % 2 == 1
    if kind == "even":   return result % 2 == 0 and result != 0
    if kind == "low":    return 1 <= result <= 18
    if kind == "high":   return 19 <= result <= 36
    if kind == "dozen1": return 1  <= result <= 12
    if kind == "dozen2": return 13 <= result <= 24
    if kind == "dozen3": return 25 <= result <= 36
    if kind == "col1":   return result % 3 == 1
    if kind == "col2":   return result % 3 == 2
    if kind == "col3":   return result % 3 == 0
    return False

bp = Blueprint("roulette", __name__, template_folder="templates")

@bp.route("/")
def wheel():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        recent = conn.execute(
            "SELECT * FROM roulette_spins WHERE username=? ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
    return render_template("roulette/wheel.html", user=user, me=me, recent=recent,
                           min_bet=MIN_BET, max_bet=MAX_BET_PER_SPOT,
                           red_numbers=sorted(RED_NUMBERS),
                           black_numbers=sorted(BLACK_NUMBERS))

@bp.route("/api/spin", methods=["POST"])
def api_spin():
    user = get_user()
    bets_input = request.json.get("bets", []) if request.json else []
    if not isinstance(bets_input, list) or not bets_input:
        return jsonify({"error": "Place at least one bet"}), 400

    parsed = []
    total_bet = 0
    for b in bets_input:
        try:
            kind = str(b.get("kind"))
            target = int(b.get("target", 0))
            amount = int(b.get("amount", 0))
        except Exception:
            return jsonify({"error": "Bad bet"}), 400
        if kind not in PAYOUTS:
            return jsonify({"error": f"Unknown bet: {kind}"}), 400
        if kind == "straight" and (target < 0 or target > 36):
            return jsonify({"error": "Straight target 0-36"}), 400
        if amount < 1 or amount > MAX_BET_PER_SPOT:
            return jsonify({"error": f"Bet 1-{MAX_BET_PER_SPOT}"}), 400
        parsed.append((kind, target, amount))
        total_bet += amount
    if total_bet < MIN_BET:
        return jsonify({"error": f"Total bet min {MIN_BET}"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < total_bet:
            return jsonify({"error": "Not enough chips"}), 400
        db.adjust_chips(conn, user, -total_bet, "roulette_bet")

    result = random.randint(0, 36)
    result_color = _color_of(result)

    payout = 0
    winning_bets = []
    for kind, target, amount in parsed:
        if _resolve_bet(kind, target, result):
            win = amount * (PAYOUTS[kind] + 1)  # includes returned stake
            payout += win
            winning_bets.append({"kind": kind, "target": target, "amount": amount, "win": win})

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "roulette_win")
        cur = conn.execute(
            "INSERT INTO roulette_spins (username, bets, total_bet, result, color, payout) VALUES (?,?,?,?,?,?)",
            (user, json.dumps([{"kind": k, "target": t, "amount": a} for k, t, a in parsed]),
             total_bet, result, result_color, payout)
        )
        spin_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "roulette", spin_id, item_name="ROULETTE", metadata={
        "result":       result,
        "color":        result_color,
        "total_bet":    total_bet,
        "payout":       payout,
        "net":          payout - total_bet,
        "winning_bets": winning_bets,
    })

    return jsonify({
        "result":       result,
        "color":        result_color,
        "payout":       payout,
        "total_bet":    total_bet,
        "net":          payout - total_bet,
        "winning_bets": winning_bets,
        "new_balance":  new_balance,
    })
