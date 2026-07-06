import json
import random
import threading

from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

ENTRY_FEE = 25

CATEGORIES = [
    "ones", "twos", "threes", "fours", "fives", "sixes",
    "three_kind", "four_kind", "full_house",
    "small_straight", "large_straight", "yahtzee", "chance",
]
UPPER = CATEGORIES[:6]

CATEGORY_LABELS = {
    "ones":           "ONES",
    "twos":           "TWOS",
    "threes":         "THREES",
    "fours":          "FOURS",
    "fives":          "FIVES",
    "sixes":          "SIXES",
    "three_kind":     "3 OF A KIND",
    "four_kind":      "4 OF A KIND",
    "full_house":     "FULL HOUSE",
    "small_straight": "SMALL STRAIGHT",
    "large_straight": "LARGE STRAIGHT",
    "yahtzee":        "YAHTZEE",
    "chance":         "CHANCE",
}

_games = {}
_games_lock = threading.Lock()


def _score(cat, dice):
    counts = {}
    for d in dice:
        counts[d] = counts.get(d, 0) + 1
    total = sum(dice)
    unique = set(dice)

    if cat in UPPER:
        n = {"ones": 1, "twos": 2, "threes": 3, "fours": 4, "fives": 5, "sixes": 6}[cat]
        return sum(d for d in dice if d == n)
    if cat == "three_kind":
        return total if any(c >= 3 for c in counts.values()) else 0
    if cat == "four_kind":
        return total if any(c >= 4 for c in counts.values()) else 0
    if cat == "full_house":
        vals = sorted(counts.values())
        return 25 if vals == [2, 3] else 0
    if cat == "small_straight":
        for run in ([1,2,3,4], [2,3,4,5], [3,4,5,6]):
            if all(v in unique for v in run):
                return 30
        return 0
    if cat == "large_straight":
        if unique in ({1,2,3,4,5}, {2,3,4,5,6}):
            return 40
        return 0
    if cat == "yahtzee":
        return 50 if any(c == 5 for c in counts.values()) else 0
    if cat == "chance":
        return total
    return 0


def _upper_total(scorecard):
    return sum(scorecard.get(c, 0) or 0 for c in UPPER)


def _grand_total(scorecard):
    total = sum(v or 0 for v in scorecard.values())
    if _upper_total(scorecard) >= 63:
        total += 35
    return total


def _payout_for_score(score):
    if score >= 300: return 250
    if score >= 250: return 100
    if score >= 200: return 50
    if score >= 150: return ENTRY_FEE
    return 0


def _serialize(state):
    return {
        "dice":        state["dice"],
        "held":        state["held"],
        "rolls_left":  state["rolls_left"],
        "turn":        state["turn"],
        "scorecard":   state["scorecard"],
        "status":      state["status"],
        "upper_total": _upper_total(state["scorecard"]),
        "grand_total": _grand_total(state["scorecard"]),
        "preview":     {c: _score(c, state["dice"]) for c in CATEGORIES if state["scorecard"].get(c) is None and state["rolls_left"] < 3},
    }


bp = Blueprint("yahtzee", __name__, template_folder="templates")


@bp.route("/")
def table():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        best = conn.execute(
            "SELECT MAX(total_score) as best FROM yahtzee_games WHERE username=?",
            (user,)
        ).fetchone()["best"]
        leaderboard = conn.execute("""
            SELECT username, MAX(total_score) as best_score, COUNT(*) as games
            FROM yahtzee_games
            GROUP BY username
            ORDER BY best_score DESC
            LIMIT 10
        """).fetchall()
    with _games_lock:
        current = _games.get(user)
        state = _serialize(current) if current else None
    return render_template("yahtzee/table.html", user=user, me=me,
                           state=state, best=best, leaderboard=leaderboard,
                           entry_fee=ENTRY_FEE, categories=CATEGORIES,
                           category_labels=CATEGORY_LABELS)


@bp.route("/api/new", methods=["POST"])
def api_new():
    user = get_user()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()
        if me["chips"] < ENTRY_FEE:
            return jsonify({"error": f"Need {ENTRY_FEE} tickets"}), 400
        db.adjust_chips(conn, user, -ENTRY_FEE, "yahtzee_entry")
        new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]

    with _games_lock:
        _games[user] = {
            "dice":       [random.randint(1, 6) for _ in range(5)],
            "held":       [False] * 5,
            "rolls_left": 2,   # first roll happened on new; 2 more available
            "turn":       1,
            "scorecard":  {c: None for c in CATEGORIES},
            "status":     "playing",
        }
        payload = _serialize(_games[user])
    return jsonify({"state": payload, "new_balance": new_balance})


@bp.route("/api/roll", methods=["POST"])
def api_roll():
    user = get_user()
    held = request.json.get("held", [False] * 5) if request.json else [False] * 5
    if not isinstance(held, list) or len(held) != 5:
        return jsonify({"error": "Bad held array"}), 400

    with _games_lock:
        state = _games.get(user)
        if not state or state["status"] != "playing":
            return jsonify({"error": "No active game"}), 400
        if state["rolls_left"] <= 0:
            return jsonify({"error": "No rolls left, must score"}), 400
        state["held"] = [bool(h) for h in held]
        for i in range(5):
            if not state["held"][i]:
                state["dice"][i] = random.randint(1, 6)
        state["rolls_left"] -= 1
        payload = _serialize(state)
    return jsonify({"state": payload})


@bp.route("/api/score", methods=["POST"])
def api_score():
    user = get_user()
    cat = request.json.get("category") if request.json else None
    if cat not in CATEGORIES:
        return jsonify({"error": "Bad category"}), 400

    with _games_lock:
        state = _games.get(user)
        if not state or state["status"] != "playing":
            return jsonify({"error": "No active game"}), 400
        if state["scorecard"].get(cat) is not None:
            return jsonify({"error": "Category already scored"}), 400
        if state["rolls_left"] == 3:
            return jsonify({"error": "Must roll first"}), 400
        state["scorecard"][cat] = _score(cat, state["dice"])
        state["turn"] += 1

        if state["turn"] > 13:
            state["status"] = "completed"
            total = _grand_total(state["scorecard"])
            payload = _serialize(state)
            game_state = state
            _games.pop(user, None)
        else:
            # New turn: fresh roll
            state["dice"] = [random.randint(1, 6) for _ in range(5)]
            state["held"] = [False] * 5
            state["rolls_left"] = 2
            payload = _serialize(state)
            game_state = None

    if game_state:
        total = _grand_total(game_state["scorecard"])
        payout = _payout_for_score(total)
        with db.get_db() as conn:
            if payout > 0:
                db.adjust_chips(conn, user, payout, "yahtzee_payout")
            cur = conn.execute(
                "INSERT INTO yahtzee_games (username, scorecard, total_score) VALUES (?, ?, ?)",
                (user, json.dumps(game_state["scorecard"]), total)
            )
            game_row_id = cur.lastrowid
            new_balance = conn.execute("SELECT chips FROM users WHERE username=?", (user,)).fetchone()["chips"]
        stats_emit.emit(user, "yahtzee", game_row_id, item_name="YAHTZEE", metadata={
            "total_score": total, "payout": payout,
            "net": payout - ENTRY_FEE,
            "yahtzees": 1 if game_state["scorecard"].get("yahtzee") == 50 else 0,
        })
        return jsonify({
            "state": payload,
            "total": total,
            "payout": payout,
            "new_balance": new_balance,
        })

    return jsonify({"state": payload})
