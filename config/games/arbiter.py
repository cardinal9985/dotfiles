"""Shared tiebreaker helper - Coin Flip or Rock Paper Scissors, randomly.

Called from any game that hits a tie/ambiguous outcome. Winner gets +100 chips
with a toast notification. All rulings logged to arbiter_calls for the ledger.
"""

import random

import db

ARBITER_PRIZE = 100
RPS_CHOICES = ["rock", "paper", "scissors"]
RPS_BEATS   = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

def call_arbiter(user_a, user_b, reason=""):
    """Randomly resolve a tie between user_a and user_b.

    Returns dict {
        mode:    'coin' | 'rps',
        winner:  username,
        loser:   username,
        detail:  {...}   # coin: {a_side, b_side, roll}; rps: {a, b}
        prize:   int,
    }
    """
    mode = random.choice(["coin", "rps"])
    if mode == "coin":
        a_side = random.choice(["heads", "tails"])
        b_side = "tails" if a_side == "heads" else "heads"
        roll   = random.choice(["heads", "tails"])
        winner = user_a if a_side == roll else user_b
        detail = {"a_side": a_side, "b_side": b_side, "roll": roll}
    else:
        while True:
            a = random.choice(RPS_CHOICES)
            b = random.choice(RPS_CHOICES)
            if a == b:
                continue
            winner = user_a if RPS_BEATS[a] == b else user_b
            detail = {"a": a, "b": b}
            break
    loser = user_b if winner == user_a else user_a

    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO arbiter_calls (winner, loser, mode, reason) VALUES (?, ?, ?, ?)",
            (winner, loser, mode, reason)
        )
        db.adjust_chips(conn, winner, ARBITER_PRIZE, f"arbiter_{reason or 'tie'}")

    return {
        "mode":   mode,
        "winner": winner,
        "loser":  loser,
        "detail": detail,
        "prize":  ARBITER_PRIZE,
        "reason": reason,
    }
