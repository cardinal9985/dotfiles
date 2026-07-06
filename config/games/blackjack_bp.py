import random
import threading

from flask import Blueprint, render_template, request, jsonify, abort

import db
from shared_auth import get_user

MIN_BET = 10
MAX_BET = 10000
SHOE_DECKS = 6

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["♠", "♥", "♦", "♣"]

def _new_shoe():
    shoe = [(r, s) for _ in range(SHOE_DECKS) for r in RANKS for s in SUITS]
    random.shuffle(shoe)
    return shoe

def _card_value(rank):
    if rank in ("J", "Q", "K"): return 10
    if rank == "A":             return 11
    return int(rank)

def hand_totals(cards):
    """Return (best_total, is_soft) - best <= 21 if possible."""
    total = sum(_card_value(r) for r, _ in cards)
    aces  = sum(1 for r, _ in cards if r == "A")
    soft  = aces > 0 and total <= 21
    while total > 21 and aces > 0:
        total -= 10
        aces  -= 1
        soft   = False
    return total, soft

def _is_blackjack(cards):
    return len(cards) == 2 and hand_totals(cards)[0] == 21

_hands = {}  # username -> hand state
_hands_lock = threading.Lock()

bp = Blueprint("blackjack", __name__, template_folder="templates")

def _serialize(state):
    """State to send to client - hide dealer's hole card until reveal."""
    dealer_cards = state["dealer"]
    reveal = state["status"] != "playing"
    dealer_visible = dealer_cards if reveal else [dealer_cards[0], ("?", "?")]
    dtotal, _ = hand_totals(dealer_cards) if reveal else (None, False)
    player_total, player_soft = hand_totals(state["player"])
    return {
        "status":         state["status"],
        "bet":            state["bet"],
        "player":         state["player"],
        "player_total":   player_total,
        "player_soft":    player_soft,
        "dealer":         dealer_visible,
        "dealer_total":   dtotal,
        "can_double":     state["status"] == "playing" and len(state["player"]) == 2,
        "result":         state.get("result"),
        "payout":         state.get("payout", 0),
        "new_balance":    state.get("new_balance"),
    }

def _play_dealer(state):
    """Dealer draws until 17+."""
    while True:
        total, soft = hand_totals(state["dealer"])
        if total >= 17:
            break
        state["dealer"].append(state["shoe"].pop())

def _resolve(state, user):
    """Called when the hand is over. Determines result, adjusts chips, persists."""
    p_total, _ = hand_totals(state["player"])
    d_total, _ = hand_totals(state["dealer"])
    bet = state["bet"]
    player_bj = _is_blackjack(state["player"])
    dealer_bj = _is_blackjack(state["dealer"])

    if p_total > 21:
        result, payout = "loss", 0
    elif player_bj and not dealer_bj:
        result, payout = "blackjack", int(bet * 2.5)
    elif dealer_bj and not player_bj:
        result, payout = "loss", 0
    elif d_total > 21:
        result, payout = "win", bet * 2
    elif p_total > d_total:
        result, payout = "win", bet * 2
    elif p_total < d_total:
        result, payout = "loss", 0
    else:
        result, payout = "push", bet

    with db.get_db() as conn:
        if payout > 0:
            db.adjust_chips(conn, user, payout, f"blackjack_{result}")
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]
        conn.execute(
            "INSERT INTO blackjack_hands (username, bet, player_cards, dealer_cards, player_total, dealer_total, result, payout) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user, bet,
             " ".join(f"{r}{s}" for r, s in state["player"]),
             " ".join(f"{r}{s}" for r, s in state["dealer"]),
             p_total, d_total, result, payout)
        )
    state["status"]      = result
    state["result"]      = result
    state["payout"]      = payout
    state["new_balance"] = new_balance

@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        recent = conn.execute(
            "SELECT * FROM blackjack_hands WHERE username=? ORDER BY created_at DESC LIMIT 10",
            (user,)
        ).fetchall()
    with _hands_lock:
        current = _hands.get(user)
        state = _serialize(current) if current else None
    return render_template("blackjack/table.html", user=user, me=me,
                           recent=recent, state=state,
                           min_bet=MIN_BET, max_bet=MAX_BET)

@bp.route("/api/state")
def api_state():
    user = get_user()
    with _hands_lock:
        current = _hands.get(user)
    if not current:
        return jsonify({"state": None})
    return jsonify({"state": _serialize(current)})

@bp.route("/api/deal", methods=["POST"])
def api_deal():
    user = get_user()
    try:
        bet = int(request.json.get("bet", 0))
    except Exception:
        return jsonify({"error": "Invalid bet"}), 400
    if bet < MIN_BET or bet > MAX_BET:
        return jsonify({"error": f"Bet must be {MIN_BET}-{MAX_BET}"}), 400

    with _hands_lock:
        if _hands.get(user) and _hands[user].get("status") == "playing":
            return jsonify({"error": "Hand already in progress"}), 400

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < bet:
            return jsonify({"error": "Not enough chips"}), 400
        db.adjust_chips(conn, user, -bet, "blackjack_bet")

    shoe = _new_shoe()
    player = [shoe.pop(), shoe.pop()]
    dealer = [shoe.pop(), shoe.pop()]
    state = {
        "shoe": shoe, "player": player, "dealer": dealer,
        "bet": bet, "status": "playing",
    }

    if _is_blackjack(player) or _is_blackjack(dealer):
        state["status"] = "reveal"
        _resolve(state, user)

    with _hands_lock:
        _hands[user] = state

    return jsonify({"state": _serialize(state)})

@bp.route("/api/hit", methods=["POST"])
def api_hit():
    user = get_user()
    with _hands_lock:
        state = _hands.get(user)
        if not state or state["status"] != "playing":
            return jsonify({"error": "No active hand"}), 400
        state["player"].append(state["shoe"].pop())
        total, _ = hand_totals(state["player"])
        if total >= 21:
            state["status"] = "reveal"
            if total > 21:
                _resolve(state, user)
            else:
                _play_dealer(state)
                _resolve(state, user)
        payload = _serialize(state)
    return jsonify({"state": payload})

@bp.route("/api/stand", methods=["POST"])
def api_stand():
    user = get_user()
    with _hands_lock:
        state = _hands.get(user)
        if not state or state["status"] != "playing":
            return jsonify({"error": "No active hand"}), 400
        state["status"] = "reveal"
        _play_dealer(state)
        _resolve(state, user)
        payload = _serialize(state)
    return jsonify({"state": payload})

@bp.route("/api/double", methods=["POST"])
def api_double():
    user = get_user()
    with _hands_lock:
        state = _hands.get(user)
        if not state or state["status"] != "playing":
            return jsonify({"error": "No active hand"}), 400
        if len(state["player"]) != 2:
            return jsonify({"error": "Can only double on first two cards"}), 400

    with db.get_db() as conn:
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < state["bet"]:
            return jsonify({"error": "Not enough chips to double"}), 400
        db.adjust_chips(conn, user, -state["bet"], "blackjack_double")

    with _hands_lock:
        state = _hands.get(user)
        state["bet"] *= 2
        state["player"].append(state["shoe"].pop())
        state["status"] = "reveal"
        total, _ = hand_totals(state["player"])
        if total <= 21:
            _play_dealer(state)
        _resolve(state, user)
        payload = _serialize(state)
    return jsonify({"state": payload})

@bp.route("/api/clear", methods=["POST"])
def api_clear():
    """Clear the finished hand from server state so a new one can be dealt."""
    user = get_user()
    with _hands_lock:
        state = _hands.get(user)
        if state and state["status"] not in ("playing",):
            _hands.pop(user, None)
    return jsonify({"cleared": True})
