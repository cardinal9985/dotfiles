import random

from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

MIN_BET = 5
MAX_BET = 500

# Symbol, weight, label
SYMBOLS = [
    ("🍒", 30, "CHERRY"),
    ("🍋", 22, "LEMON"),
    ("🔔", 15, "BELL"),
    ("⭐", 9,  "STAR"),
    ("7",  4,  "SEVEN"),
    ("☾",  2,  "CRESCENT"),
]

# Multiplier for triple-of-a-kind (multiplier * bet = payout)
TRIPLES = {
    "🍒": 6,
    "🍋": 12,
    "🔔": 25,
    "⭐": 60,
    "7":  120,
    "☾":  500,
}
# Any 2 of a kind pays back the bet (net 0), except cherry pays 2x
DOUBLES_CHERRY = 2

def _spin():
    weighted = []
    for sym, w, _ in SYMBOLS:
        weighted.extend([sym] * w)
    return [random.choice(weighted) for _ in range(3)]

def _resolve(reels, bet):
    counts = {}
    for s in reels:
        counts[s] = counts.get(s, 0) + 1
    if 3 in counts.values():
        sym = reels[0]
        return TRIPLES.get(sym, 0) * bet, f"triple_{sym}"
    if 2 in counts.values():
        pair_sym = next(s for s, c in counts.items() if c == 2)
        if pair_sym == "🍒":
            return bet * DOUBLES_CHERRY, "pair_cherry"
        return bet, "pair"
    return 0, "miss"

bp = Blueprint("slots", __name__, template_folder="templates")

@bp.route("/")
def machine():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        recent = conn.execute(
            "SELECT * FROM slot_spins WHERE username=? ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
    return render_template("slots/machine.html", user=user, me=me, recent=recent,
                           min_bet=MIN_BET, max_bet=MAX_BET, triples=TRIPLES)

@bp.route("/api/spin", methods=["POST"])
def api_spin():
    user = get_user()
    try:
        bet = int(request.json.get("bet", 0))
    except Exception:
        return jsonify({"error": "Bad bet"}), 400
    if bet < MIN_BET or bet > MAX_BET:
        return jsonify({"error": f"Bet must be {MIN_BET}-{MAX_BET}"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < bet:
            return jsonify({"error": "Not enough chips"}), 400
        db.adjust_chips(conn, user, -bet, "slots_bet")

    reels = _spin()
    payout, combo = _resolve(reels, bet)

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, "slots_win")
        cur = conn.execute(
            "INSERT INTO slot_spins (username, bet, reels, payout, combo) VALUES (?, ?, ?, ?, ?)",
            (user, bet, " ".join(reels), payout, combo)
        )
        spin_id = cur.lastrowid
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    stats_emit.emit(user, "slots", spin_id, item_name="SLOTS", metadata={
        "bet":    bet,
        "reels":  reels,
        "combo":  combo,
        "payout": payout,
        "net":    payout - bet,
    })

    return jsonify({
        "reels":       reels,
        "payout":      payout,
        "combo":       combo,
        "bet":         bet,
        "net":         payout - bet,
        "new_balance": new_balance,
    })
