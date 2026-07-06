import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("GAMES_DB_PATH", "/tmp/games.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username    TEXT PRIMARY KEY,
    wins        INTEGER NOT NULL DEFAULT 0,
    losses      INTEGER NOT NULL DEFAULT 0,
    draws       INTEGER NOT NULL DEFAULT 0,
    rating      INTEGER NOT NULL DEFAULT 1200,
    chips       INTEGER NOT NULL DEFAULT 10000,
    chips_lifetime_won INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS games (
    id              TEXT    PRIMARY KEY,
    white           TEXT,
    black           TEXT,
    white_is_ai     INTEGER NOT NULL DEFAULT 0,
    black_is_ai     INTEGER NOT NULL DEFAULT 0,
    ai_level        INTEGER NOT NULL DEFAULT 5,
    bot_name        TEXT    NOT NULL DEFAULT '',
    variant         TEXT    NOT NULL DEFAULT 'standard',
    time_control    TEXT    NOT NULL DEFAULT 'unlimited',
    white_time_ms   INTEGER NOT NULL DEFAULT 0,
    black_time_ms   INTEGER NOT NULL DEFAULT 0,
    status          TEXT    NOT NULL DEFAULT 'waiting',
    result          TEXT,
    moves           TEXT    NOT NULL DEFAULT '',
    pgn             TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS game_analysis (
    game_id     TEXT    NOT NULL,
    move_number INTEGER NOT NULL,
    move_uci    TEXT    NOT NULL,
    evaluation  INTEGER,
    best_move   TEXT,
    PRIMARY KEY (game_id, move_number),
    FOREIGN KEY (game_id) REFERENCES games(id)
);

CREATE TABLE IF NOT EXISTS chip_transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL,
    delta       INTEGER NOT NULL,
    reason      TEXT    NOT NULL,
    game_ref    TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chip_txn_user ON chip_transactions(username, created_at DESC);

CREATE TABLE IF NOT EXISTS blackjack_hands (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT    NOT NULL,
    bet          INTEGER NOT NULL,
    player_cards TEXT    NOT NULL,
    dealer_cards TEXT    NOT NULL,
    player_total INTEGER NOT NULL,
    dealer_total INTEGER NOT NULL,
    result       TEXT    NOT NULL,
    payout       INTEGER NOT NULL,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bj_user ON blackjack_hands(username, created_at DESC);

CREATE TABLE IF NOT EXISTS arbiter_calls (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    winner     TEXT    NOT NULL,
    loser      TEXT,
    mode       TEXT    NOT NULL,
    reason     TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_arbiter_winner ON arbiter_calls(winner, created_at DESC);

CREATE TABLE IF NOT EXISTS dice_rolls (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL,
    bet_over   INTEGER NOT NULL DEFAULT 0,
    bet_under  INTEGER NOT NULL DEFAULT 0,
    bet_equal  INTEGER NOT NULL DEFAULT 0,
    d1         INTEGER NOT NULL,
    d2         INTEGER NOT NULL,
    total      INTEGER NOT NULL,
    payout     INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dice_user ON dice_rolls(username, created_at DESC);

CREATE TABLE IF NOT EXISTS roulette_spins (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL,
    bets       TEXT    NOT NULL,
    total_bet  INTEGER NOT NULL,
    result     INTEGER NOT NULL,
    color      TEXT    NOT NULL,
    payout     INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_roulette_user ON roulette_spins(username, created_at DESC);

CREATE TABLE IF NOT EXISTS connect4_games (
    id           TEXT PRIMARY KEY,
    player_a     TEXT NOT NULL,
    player_b     TEXT,
    ante         INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'waiting',
    winner       TEXT,
    board        TEXT NOT NULL DEFAULT '',
    turn         TEXT NOT NULL DEFAULT 'a',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS baccarat_hands (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL,
    bet_player    INTEGER NOT NULL DEFAULT 0,
    bet_banker    INTEGER NOT NULL DEFAULT 0,
    bet_tie       INTEGER NOT NULL DEFAULT 0,
    player_cards  TEXT    NOT NULL,
    banker_cards  TEXT    NOT NULL,
    player_total  INTEGER NOT NULL,
    banker_total  INTEGER NOT NULL,
    result        TEXT    NOT NULL,
    payout        INTEGER NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bacc_user ON baccarat_hands(username, created_at DESC);

CREATE TABLE IF NOT EXISTS slot_spins (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL,
    bet        INTEGER NOT NULL,
    reels      TEXT    NOT NULL,
    payout     INTEGER NOT NULL,
    combo      TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_slots_user ON slot_spins(username, created_at DESC);

CREATE TABLE IF NOT EXISTS war_games (
    id           TEXT PRIMARY KEY,
    player_a     TEXT NOT NULL,
    player_b     TEXT,
    ante         INTEGER NOT NULL,
    rounds_total INTEGER NOT NULL DEFAULT 5,
    a_score      INTEGER NOT NULL DEFAULT 0,
    b_score      INTEGER NOT NULL DEFAULT 0,
    status       TEXT    NOT NULL DEFAULT 'waiting',
    winner       TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);
"""

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)
        ucols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        for col, ddl in [
            ("rating",             "ALTER TABLE users ADD COLUMN rating INTEGER NOT NULL DEFAULT 1200"),
            ("chips",              "ALTER TABLE users ADD COLUMN chips INTEGER NOT NULL DEFAULT 10000"),
            ("chips_lifetime_won", "ALTER TABLE users ADD COLUMN chips_lifetime_won INTEGER NOT NULL DEFAULT 0"),
        ]:
            if col not in ucols:
                conn.execute(ddl)
        gcols = {r[1] for r in conn.execute("PRAGMA table_info(games)").fetchall()}
        for col, ddl in [
            ("bot_name",      "ALTER TABLE games ADD COLUMN bot_name TEXT NOT NULL DEFAULT ''"),
            ("variant",       "ALTER TABLE games ADD COLUMN variant TEXT NOT NULL DEFAULT 'standard'"),
            ("time_control",  "ALTER TABLE games ADD COLUMN time_control TEXT NOT NULL DEFAULT 'unlimited'"),
            ("white_time_ms", "ALTER TABLE games ADD COLUMN white_time_ms INTEGER NOT NULL DEFAULT 0"),
            ("black_time_ms", "ALTER TABLE games ADD COLUMN black_time_ms INTEGER NOT NULL DEFAULT 0"),
        ]:
            if col not in gcols:
                conn.execute(ddl)

INITIAL_RATING = 1200
K_FACTOR = 32
RATING_FLOOR = 100

def elo_update(rating_a, rating_b, score_a, k=K_FACTOR):
    exp_a = 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))
    delta = k * (score_a - exp_a)
    new_a = max(RATING_FLOOR, round(rating_a + delta))
    new_b = max(RATING_FLOOR, round(rating_b - delta))
    return new_a, new_b

def ensure_user(conn, username):
    conn.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))

def adjust_chips(conn, username, delta, reason, game_ref=None):
    """Apply a chip delta to a user's balance, log it in transactions."""
    if delta == 0:
        return
    ensure_user(conn, username)
    conn.execute("UPDATE users SET chips = chips + ? WHERE username = ?", (delta, username))
    if delta > 0:
        conn.execute("UPDATE users SET chips_lifetime_won = chips_lifetime_won + ? WHERE username = ?", (delta, username))
    conn.execute(
        "INSERT INTO chip_transactions (username, delta, reason, game_ref) VALUES (?, ?, ?, ?)",
        (username, delta, reason, game_ref)
    )

def record_result(conn, game_id, result):
    game = conn.execute("SELECT white, black, white_is_ai, black_is_ai FROM games WHERE id=?", (game_id,)).fetchone()
    if not game:
        return None
    white, black = game["white"], game["black"]
    white_is_ai, black_is_ai = game["white_is_ai"], game["black_is_ai"]

    if result == "white_wins":
        if not white_is_ai and white:
            conn.execute("UPDATE users SET wins=wins+1 WHERE username=?", (white,))
        if not black_is_ai and black:
            conn.execute("UPDATE users SET losses=losses+1 WHERE username=?", (black,))
    elif result == "black_wins":
        if not white_is_ai and white:
            conn.execute("UPDATE users SET losses=losses+1 WHERE username=?", (white,))
        if not black_is_ai and black:
            conn.execute("UPDATE users SET wins=wins+1 WHERE username=?", (black,))
    elif result == "draw":
        if not white_is_ai and white:
            conn.execute("UPDATE users SET draws=draws+1 WHERE username=?", (white,))
        if not black_is_ai and black:
            conn.execute("UPDATE users SET draws=draws+1 WHERE username=?", (black,))

    if not white_is_ai and not black_is_ai and white and black and result in ("white_wins", "black_wins", "draw"):
        rows = conn.execute(
            "SELECT username, rating FROM users WHERE username IN (?, ?)", (white, black)
        ).fetchall()
        ratings = {r["username"]: r["rating"] for r in rows}
        w_rating = ratings.get(white, INITIAL_RATING)
        b_rating = ratings.get(black, INITIAL_RATING)
        score_w = {"white_wins": 1.0, "black_wins": 0.0, "draw": 0.5}[result]
        new_w, new_b = elo_update(w_rating, b_rating, score_w)
        conn.execute("UPDATE users SET rating=? WHERE username=?", (new_w, white))
        conn.execute("UPDATE users SET rating=? WHERE username=?", (new_b, black))
        return {
            "white": {"user": white, "old": w_rating, "new": new_w, "delta": new_w - w_rating},
            "black": {"user": black, "old": b_rating, "new": new_b, "delta": new_b - b_rating},
        }
    return None

def get_leaderboard(conn, limit=10):
    return conn.execute("""
        SELECT username, wins, losses, draws, rating,
               (wins + losses + draws) AS total,
               CASE WHEN (wins + losses + draws) = 0 THEN 0.0
                    ELSE ROUND(wins * 1.0 / (wins + losses + draws) * 100, 1)
               END AS win_pct
        FROM users
        WHERE (wins + losses + draws) > 0
        ORDER BY rating DESC, wins DESC
        LIMIT ?
    """, (limit,)).fetchall()

def get_arbiter_ledger(conn, limit=10):
    return conn.execute("""
        SELECT winner AS username,
               COUNT(*) AS rulings,
               SUM(CASE WHEN mode='coin' THEN 1 ELSE 0 END) AS coin_wins,
               SUM(CASE WHEN mode='rps'  THEN 1 ELSE 0 END) AS rps_wins
        FROM arbiter_calls
        GROUP BY winner
        ORDER BY rulings DESC
        LIMIT ?
    """, (limit,)).fetchall()

def get_chip_leaderboard(conn, limit=10):
    return conn.execute("""
        SELECT username, chips, chips_lifetime_won
        FROM users
        WHERE chips_lifetime_won > 0 OR chips <> 10000
        ORDER BY chips_lifetime_won DESC, chips DESC
        LIMIT ?
    """, (limit,)).fetchall()

def get_user_games(conn, username, limit=20):
    return conn.execute("""
        SELECT id, white, black, white_is_ai, black_is_ai, variant, result, created_at, completed_at
        FROM games
        WHERE (white=? OR black=?) AND status='completed'
        ORDER BY completed_at DESC
        LIMIT ?
    """, (username, username, limit)).fetchall()

def get_active_games(conn):
    return conn.execute("""
        SELECT id, white, black, white_is_ai, black_is_ai, status, ai_level, variant, created_at
        FROM games
        WHERE status IN ('waiting', 'active')
        ORDER BY created_at DESC
        LIMIT 20
    """).fetchall()
