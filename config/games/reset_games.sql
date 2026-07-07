-- Rec Deck: reset all balances to 5000, wipe game history + player stats.
-- Run manually on ishimura:
--   sudo -u games sqlite3 /persist/games/games.db < reset_games.sql

BEGIN;

-- Reset user counters + streaks (keep the rows, they're the identity)
UPDATE users SET
    chips              = 5000,
    chips_lifetime_won = 0,
    wins               = 0,
    losses             = 0,
    draws              = 0,
    rating             = 1200,
    last_stipend_at    = NULL,
    last_wordle_date   = NULL,
    wordle_streak      = 0,
    wordle_best_streak = 0;

-- Wipe all game history + transaction ledger
DELETE FROM chip_transactions;
DELETE FROM games;
DELETE FROM game_analysis;
DELETE FROM blackjack_hands;
DELETE FROM arbiter_calls;
DELETE FROM dice_rolls;
DELETE FROM roulette_spins;
DELETE FROM connect4_games;
DELETE FROM highstriker_attempts;
DELETE FROM ringtoss_rounds;
DELETE FROM balloonpop_rounds;
DELETE FROM skeeball_rounds;
DELETE FROM whack_rounds;
DELETE FROM snake_runs;
DELETE FROM reaction_attempts;
DELETE FROM duckrace_games;
DELETE FROM yahtzee_games;
DELETE FROM baccarat_hands;
DELETE FROM slot_spins;
DELETE FROM war_games;
DELETE FROM tictactoe_games;
DELETE FROM wordle_attempts;

COMMIT;
VACUUM;
