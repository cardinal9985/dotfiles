import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Blueprint, render_template, request, jsonify

import db
import stats_emit
from shared_auth import get_user

MAX_GUESSES = 6
WORD_LEN    = 5

PAYOUT_BY_GUESSES = {1: 500, 2: 200, 3: 100, 4: 50, 5: 25, 6: 10}
STREAK_BONUS_PCT_PER_DAY = 5
STREAK_BONUS_MAX_PCT     = 100

_DATA = Path(__file__).parent / "data" / "wordle_words.txt"

def _load_words():
    words = []
    for line in _DATA.read_text().splitlines():
        w = line.strip().lower()
        if len(w) == WORD_LEN and w.isalpha():
            words.append(w)
    seen = set()
    out = []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out

WORDS = _load_words()

def _today():
    return date.today().isoformat()

def _word_for_date(iso):
    idx = int(hashlib.sha256(iso.encode()).hexdigest(), 16) % len(WORDS)
    return WORDS[idx]

def _score_guess(guess, answer):
    result = ["gray"] * WORD_LEN
    ans = list(answer)
    for i, c in enumerate(guess):
        if c == ans[i]:
            result[i] = "green"
            ans[i] = None
    for i, c in enumerate(guess):
        if result[i] == "gray" and c in ans:
            result[i] = "yellow"
            ans[ans.index(c)] = None
    return result

def _seconds_to_midnight_utc():
    now = datetime.utcnow()
    tomorrow_midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    return int((tomorrow_midnight - now).total_seconds())

def _get_or_create_today(conn, user, today):
    row = conn.execute(
        "SELECT * FROM wordle_attempts WHERE username=? AND date=?",
        (user, today)
    ).fetchone()
    if row:
        return row
    conn.execute(
        "INSERT INTO wordle_attempts (username, date) VALUES (?, ?)",
        (user, today)
    )
    return conn.execute(
        "SELECT * FROM wordle_attempts WHERE username=? AND date=?",
        (user, today)
    ).fetchone()

def _apply_streak(conn, user, solved, today):
    row = conn.execute(
        "SELECT last_wordle_date, wordle_streak, wordle_best_streak FROM users WHERE username=?",
        (user,)
    ).fetchone()
    last   = row["last_wordle_date"] if row else None
    streak = row["wordle_streak"] if row else 0
    best   = row["wordle_best_streak"] if row else 0
    yday   = (date.today() - timedelta(days=1)).isoformat()
    if not solved:
        new_streak = 0
    elif last == yday:
        new_streak = streak + 1
    else:
        new_streak = 1
    new_best = max(best, new_streak)
    conn.execute(
        "UPDATE users SET last_wordle_date=?, wordle_streak=?, wordle_best_streak=? WHERE username=?",
        (today, new_streak, new_best, user)
    )
    return new_streak, new_best

bp = Blueprint("wordle", __name__, template_folder="templates")

@bp.route("/")
def table():
    user = get_user()
    today = _today()
    with db.get_db() as conn:
        db.ensure_user(conn, user)
        me = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        attempt = _get_or_create_today(conn, user, today)
        today_players = conn.execute(
            """SELECT username, solved, guess_count
                 FROM wordle_attempts
                WHERE date=? AND (solved=1 OR guess_count>=?)
             ORDER BY solved DESC, guess_count ASC""",
            (today, MAX_GUESSES)
        ).fetchall()
        history = conn.execute(
            """SELECT date, solved, guess_count, payout, streak_after
                 FROM wordle_attempts
                WHERE username=? ORDER BY date DESC LIMIT 14""",
            (user,)
        ).fetchall()

    guesses = json.loads(attempt["guesses_json"])
    answer = _word_for_date(today)
    scored = [{"guess": g, "feedback": _score_guess(g, answer)} for g in guesses]
    finished = bool(attempt["solved"]) or attempt["guess_count"] >= MAX_GUESSES
    reveal = answer if finished and not attempt["solved"] else None

    return render_template(
        "wordle/table.html",
        user=user, me=me,
        guesses=scored,
        finished=finished,
        solved=bool(attempt["solved"]),
        payout=attempt["payout"],
        streak_after=attempt["streak_after"],
        current_streak=me["wordle_streak"] if me else 0,
        best_streak=me["wordle_best_streak"] if me else 0,
        reveal=reveal,
        max_guesses=MAX_GUESSES,
        word_len=WORD_LEN,
        today=today,
        next_seconds=_seconds_to_midnight_utc(),
        today_players=today_players,
        history=history,
    )

@bp.route("/api/guess", methods=["POST"])
def api_guess():
    user = get_user()
    today = _today()
    payload = request.get_json(silent=True) or {}
    guess = (payload.get("guess") or "").lower().strip()
    if len(guess) != WORD_LEN or not guess.isalpha():
        return jsonify({"error": "Must be 5 letters"}), 400
    answer = _word_for_date(today)

    with db.get_db() as conn:
        db.ensure_user(conn, user)
        attempt = _get_or_create_today(conn, user, today)
        if attempt["solved"] or attempt["guess_count"] >= MAX_GUESSES:
            return jsonify({"error": "Already done for today"}), 400
        guesses = json.loads(attempt["guesses_json"])
        guesses.append(guess)
        guess_count = len(guesses)
        solved = (guess == answer)
        finished = solved or guess_count >= MAX_GUESSES

        payout = 0
        streak_after = attempt["streak_after"]
        if finished:
            new_streak, _new_best = _apply_streak(conn, user, solved, today)
            streak_after = new_streak
            if solved:
                base = PAYOUT_BY_GUESSES[guess_count]
                bonus_pct = min(max(new_streak - 1, 0) * STREAK_BONUS_PCT_PER_DAY,
                                STREAK_BONUS_MAX_PCT)
                payout = int(base * (1 + bonus_pct / 100))
                db.adjust_chips(conn, user, payout, f"wordle_solve_{today}")

        conn.execute(
            """UPDATE wordle_attempts
                  SET guesses_json=?, solved=?, guess_count=?, payout=?, streak_after=?
                WHERE id=?""",
            (json.dumps(guesses), 1 if solved else 0, guess_count,
             payout, streak_after, attempt["id"])
        )

        if finished:
            stats_emit.emit(user, "wordle", str(attempt["id"]),
                            item_name="DAILY WORDLE", metadata={
                "date":    today,
                "solved":  solved,
                "guesses": guess_count,
                "payout":  payout,
                "streak":  streak_after,
            })

        me = conn.execute(
            "SELECT chips, wordle_best_streak FROM users WHERE username=?",
            (user,)
        ).fetchone()

    feedback = _score_guess(guess, answer)
    return jsonify({
        "feedback":     feedback,
        "solved":       solved,
        "finished":     finished,
        "guess_count":  guess_count,
        "remaining":    MAX_GUESSES - guess_count,
        "payout":       payout,
        "streak":       streak_after,
        "best_streak":  me["wordle_best_streak"],
        "answer":       answer if finished and not solved else None,
        "new_balance":  me["chips"],
    })
