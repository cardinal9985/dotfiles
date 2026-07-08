# USG Rec Deck - Games Hub Design (`rec.ishimura.lol`)

**Status:** absorbed from notes/memory/project_games_hub2.md on 2026-07-09. Chess + Blackjack shipped (2026-07-06); all other tiles pending. Achievement system deferred to stats-extension spec.

**One-liner:** Multi-game hub at `rec.ishimura.lol` served from `config/games/` on ishimura port 5001 (systemd `ishimura-games`). Flask factory + Blueprints per game, SocketIO with namespace-per-game. Shared users/chips schema at `/persist/games/games.db`. Currency called TICKETS in UI (DB column stays `chips` for continuity).

## Stack

- Flask factory + Blueprints per game
- SocketIO namespace per game
- Shared users/chips schema at `/persist/games/games.db` (migrated from old `/persist/chess/chess.db`, original preserved for rollback)
- VoidAuth via Remote-User header
- Sops keys stay named `chess/*` for continuity (secret_key + discord_webhook), aliased into `games.env` under new variable names in `games.nix`

## Grid plan (17 rows x 4 = 68 tiles)

DAILY row sits above the games catalog (right after DOSSIER section on hub) - special positioning because dailies are gated on time rather than skill/tickets.

| Row | Category | Games |
|---|---|---|
| DAILY | (above catalog) | Wordle, Chess Puzzle, Mini Crossword, Daily Trivia |
| 1 | Skill / Elo-rated | Chess, Checkers, Backgammon, Hnefatafl |
| 2 | Casino table | Poker, Blackjack, Roulette, Baccarat |
| 3 | Dice | Dice, Liar's Dice, Yahtzee, Farkle |
| 4 | Quick / party | Connect 4, War, Duck Race, Slots |
| 5 | Arcade retro solo | Snake, Tetris, Whack-a-Mole, Reaction Time |
| 6 | Arcade real-time | Pong, Air Hockey, Tron, Bomberman |
| 7 | Carnival aim/timing | High Striker, Ring Toss, Balloon Pop, Skee-Ball |
| 8 | Carnival midway | Plinko, Prize Claw, Coin Pusher, Duck Hunt |
| 9 | Showtime party | Pictionary, Wheel of Fortune, Codenames, Werewolf |
| 10 | Showtime game show | Millionaire, Deal or No Deal, Family Feud, Press Your Luck |
| 11 | Standoff / phys duel | Arm Wrestling, Tug of War, Stroop, Chicken |
| 12 | Codex / puzzles | Cryptogram, Nonogram, Mastermind, Logic Grid |
| 13 | Draws / community | Lotto, Powerball, Bingo, Keno |
| 14 | Seance / occult | Ouija, Tarot, Zoltar, Ghost Hunt |
| 15 | Pub / bar sports | Darts, Pool, Bowling, Shuffleboard |
| 16 | Memory / recall | Simon Says, Memory Match, Kim's Game, Speed Cards |
| 17 | Strategy / short 1v1 | Reversi, Nim, Mancala, Nine Men's Morris |

## Specific mechanics locked in

### Arm Wrestling (verified from Outlast Trials 2026-07-07)

NOT a masher. Rotating pointer on a shared dial. Small green "YES" zone + several orange/red "NO" zones on the wheel. Both players click to time a hit as the pointer sweeps:

- Land in YES zone = push opponent back, extend your streak
- Land in NO zone or miss YES = you get pushed back
- Both players miss on same rotation = nobody moves (safety net)
- Streak increases pointer speed each successive hit, making precision harder
- Streak/momentum indicator: horizontal bar of 3 red icons above/below wheel (Outlast style)
- First to shove opponent off their end wins the round

Reference screenshots at `~/downloads/1.png` (wheel closeup) and `~/downloads/2.jpg` (in-game scene).

### Stroop (verified from Outlast Trials 2026-07-07)

Cognitive interference game.

- TV screen shows color word (e.g. "YELLOW") rendered in mismatched ink (e.g. green ink)
- Player must press the button labeled with the INK COLOR (green), NOT the written word
- Time pressure + cognitive interference = fast, wrong-answer-prone
- Each correct answer scores, each miss (or timeout) penalizes
- Round timer or first-to-N-points structure
- PvP: both players see same prompt, first correct scores; wrong answers lock you out for a beat

### Pong (verified from Outlast Trials 2026-07-07)

NOT classic 2D pong. Ping-pong / table tennis in 3D perspective.

- Players stand on opposite sides of a table with a net
- Serve, volley, spike mechanics with different button inputs
- Straight shots vs high shots
- Spiking requires: ball on upward trajectory near its peak, not too far back on your side, and at least 1/4 stamina
- Ball must bounce on opponent's side; misses = point for opponent
- Bad hits can spike the ball into your OWN net (self-fault)
- 1v1 humans OR vs BOT with adjustable AI level (chess pattern - one tile handles both)

Streaks table planned: `(username, game_type, current_streak, best_streak, last_played_date, total_wins)`. Reset `current_streak` to 0 if `last_played_date < today - 1 day` when user opens a daily game.

DRAWS row (lottery/bingo/raffle, 8 games across 2 rows) discussed but not yet placed on hub - deferred until user confirms tile picks and row structure.

## Status (2026-07-06)

- **Chess**: shipped - all variants + bots + time controls + duck chess
- **Blackjack**: shipped - 6-deck shoe, 3:2 blackjack, no split/insurance yet
- **All others**: not started

## Roadmap

- Poker (Texas Hold'em NL first, all seat sizes, humans-only; then Omaha PL, Short Deck, 5-Card Draw)
- Bots for Hold'em + Blackjack (ROOKIE/OFFICER/CAPTAIN tiers, heuristic)
- Dice (variant TBD - hi-lo / sic bo / craps)
- Liar's Dice (multi-player bluffing)
- Blackjack split + insurance (Phase 2b)
- Remaining tiles per grid

## Arbiter mechanic

Shared `resolve_tie(user_a, user_b, reason)` helper - randomly picks RPS or coin flip UI, records outcome, logs to a new `arbiter_calls` table.

**Fires from:**

- Chess draw offer accepted (optional button on game-over: "CALL THE ARBITER")
- Pre-chess "who plays white" (replaces default of game-creator=white)
- War card ties (canonical rules)
- Poker chip-off ties
- Blackjack tiebreak on identical 21s

**Prize:** Arbiter winner gets 100 free chips with a visible toast notification (`+100 TICKETS :: ARBITER RULING`) so it's clear where they came from.

**Ledger:** Visible section on `/leaderboard` page (not hidden) - "ARBITER LEDGER" showing arbiter call stats per user. Persistent rankings for a thing nobody asked for.

**Why:** Adds character across the app for near-zero cost, gives friends "wait what?" moments.

## Chip win notifications

Global toast system in `games.css` + `games.js` - shared helper `showToast(msg, kind)` that pops from top-right, auto-dismisses after ~3s.

**Wire to:**

- Blackjack: chips won on WIN/BLACKJACK/PUSH
- Arbiter: chip prize
- Future poker/dice/etc: any chip inflow
- Chess: Elo delta already shown on game-over panel, no toast needed

## Chip usage roadmap (all four approved)

- **Tipping** - transfer chips to another user; button on profile page. Social play.
- **Cosmetic titles + nameplate colors** - chip shop; buy titles ("GRAND CROUPIER") + color name in leaderboards/game history. Primary chip sink.
- **Spectator betting** - bet chips on other people's live chess/war/connect4 matches via URL. Emergent PvP watching.
- **Weekly stipend** - login bonus (~500/week). Anti-tilt / retention.

## Deferred (after all games built)

- **Tournaments** - buy-in with prize pool, bracket / Swiss format
- **Bounties** - "First to beat maxwell at war = +2000 tickets"
- **Loot boxes** - ticket cost, contains random rewards
- **Wheel of Fortune** - burn tickets, spin for random reward
- **Fortune Cookie / Magic 8-Ball** - spend ~10 tickets for a fortune. Rarely (~1%) small ticket reward, mostly flavor
- **Gift Shop** - central page to spend tickets on cosmetic titles + nameplate colors + name-glow effects. Sits alongside Rankings in top nav
- **In-game gifting (poker)** - during poker hand, spend tickets to send emoji/reaction (drink, flower, laugh) that overlays recipient's seat like Zynga Poker. Extends to war/connect4 for taunts.

## Currency naming

Currency is called TICKETS in the UI. DB column stays `chips` for continuity (no migration). All templates + toast strings + tag labels display TICKETS.

With arcade + carnival rows joining casino, "chips" was too poker-flavored. "Tickets" fits arcade/carnival/casino equally and reads as "prize tickets" from a rec deck.

## Easter eggs (backlog)

- 404 page: "IN THIS SECTOR, NO ONE CAN HEAR YOU CLICK."
- Rare marker (~0.5% page load) in starfield canvas - single red twinkling star that isn't in normal palette
- Slot machine jackpot combo: `☾ ☾ ☾` (necromorph reference) = 500x payout
- Rare flavor text after ~1% of chess games: `KENDRA: STANDBY. USG HAS ACKNOWLEDGED YOUR RESULT.` instead of standard "WHITE WINS"

Add opportunistically as we build each game.

## Achievement integration (deferred)

Games hub already emits every completion event to stats via `/webhook/games`. When stats-extension ships (see `2026-07-09-stats-extension-design.md`), the achievement engine subscribes to that event stream:

- Cross-app achievements ("watch a horror movie AND win a chess game the same night")
- Games-only achievements ("5 blackjack wins in a row", "hit the triple crescent slot jackpot", "yahtzee natural 50", "reaction time under 200ms")
- Rec room profile.html renders unlocked achievements alongside chess Elo + tickets
- Unlocks notify via toast (already-built) + Discord webhook

## Ties into

- [[stats-extension]] - subscribes to `/webhook/games` for achievements + gamerscore
- [[vtt]] - shared users/tickets, VTT is standalone but linked via nav
- [[bridge]] - Rec Deck server appears in Bridge's Media Deck card grid
- [[comms officer]] - Discord bot posts chess results + tournament updates
