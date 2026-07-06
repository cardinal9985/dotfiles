import random

from flask import Blueprint, render_template, request, jsonify

import db
from shared_auth import get_user

MIN_BET = 10
MAX_BET = 5000

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]

def _card_value(rank):
    if rank == "A":                       return 1
    if rank in ("10", "J", "Q", "K"):     return 0
    return int(rank)

def _hand_total(cards):
    return sum(_card_value(r) for r, _ in cards) % 10

def _new_shoe():
    shoe = [(r, s) for _ in range(6) for r in RANKS for s in SUITS]
    random.shuffle(shoe)
    return shoe

def _draw_baccarat_hand(shoe):
    """Standard Punto Banco deal with third-card rules."""
    player = [shoe.pop(), shoe.pop()]
    banker = [shoe.pop(), shoe.pop()]
    p_total = _hand_total(player)
    b_total = _hand_total(banker)

    # Naturals: 8 or 9, both stand
    if p_total >= 8 or b_total >= 8:
        return player, banker

    # Player draw rule: hit on 0-5, stand on 6-7
    player_third = None
    if p_total <= 5:
        player_third = shoe.pop()
        player.append(player_third)

    # Banker draw rule
    if player_third is None:
        # Player stood, banker hits on 0-5, stands on 6-7
        if b_total <= 5:
            banker.append(shoe.pop())
    else:
        pt3_val = _card_value(player_third[0])
        # Complex banker rules based on banker total + player's third card
        if b_total <= 2:
            banker.append(shoe.pop())
        elif b_total == 3 and pt3_val != 8:
            banker.append(shoe.pop())
        elif b_total == 4 and pt3_val in (2, 3, 4, 5, 6, 7):
            banker.append(shoe.pop())
        elif b_total == 5 and pt3_val in (4, 5, 6, 7):
            banker.append(shoe.pop())
        elif b_total == 6 and pt3_val in (6, 7):
            banker.append(shoe.pop())
        # banker 7 stands

    return player, banker

bp = Blueprint("baccarat", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        recent = conn.execute(
            "SELECT * FROM baccarat_hands WHERE username=? ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
    return render_template("baccarat/table.html", user=user, me=me, recent=recent,
                           min_bet=MIN_BET, max_bet=MAX_BET)

@bp.route("/api/deal", methods=["POST"])
def api_deal():
    user = get_user()
    try:
        bp_bet = int(request.json.get("bet_player", 0))
        bb_bet = int(request.json.get("bet_banker", 0))
        bt_bet = int(request.json.get("bet_tie", 0))
    except Exception:
        return jsonify({"error": "Bad bet"}), 400
    total_bet = bp_bet + bb_bet + bt_bet
    if total_bet <= 0:
        return jsonify({"error": "Place at least one bet"}), 400
    for b in (bp_bet, bb_bet, bt_bet):
        if b < 0 or b > MAX_BET:
            return jsonify({"error": f"Each bet must be 0-{MAX_BET}"}), 400
    if total_bet < MIN_BET:
        return jsonify({"error": f"Total bet must be >= {MIN_BET}"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < total_bet:
            return jsonify({"error": "Not enough chips"}), 400
        db.adjust_chips(conn, user, -total_bet, "baccarat_bet")

    shoe = _new_shoe()
    player, banker = _draw_baccarat_hand(shoe)
    p_total = _hand_total(player)
    b_total = _hand_total(banker)

    if p_total > b_total:  result = "player"
    elif b_total > p_total: result = "banker"
    else:                   result = "tie"

    payout = 0
    if result == "player" and bp_bet > 0:
        payout += bp_bet * 2  # 1:1 + stake
    if result == "banker" and bb_bet > 0:
        payout += bb_bet + int(bb_bet * 0.95)  # 0.95:1 + stake
    if result == "tie":
        if bt_bet > 0:
            payout += bt_bet + bt_bet * 8  # 8:1 + stake
        # Player and Banker bets are pushed on a tie
        if bp_bet > 0: payout += bp_bet
        if bb_bet > 0: payout += bb_bet

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, f"baccarat_{result}")
        conn.execute(
            "INSERT INTO baccarat_hands (username, bet_player, bet_banker, bet_tie, player_cards, banker_cards, player_total, banker_total, result, payout) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user, bp_bet, bb_bet, bt_bet,
             " ".join(f"{r}{s}" for r, s in player),
             " ".join(f"{r}{s}" for r, s in banker),
             p_total, b_total, result, payout)
        )
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    return jsonify({
        "player":       player,
        "banker":       banker,
        "player_total": p_total,
        "banker_total": b_total,
        "result":       result,
        "payout":       payout,
        "total_bet":    total_bet,
        "net":          payout - total_bet,
        "new_balance":  new_balance,
    })
