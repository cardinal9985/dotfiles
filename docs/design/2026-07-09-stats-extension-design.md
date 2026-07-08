# Stats Extension - Profiles, Achievements, Taste Profile

**Status:** design brainstormed 2026-07-09, ready for scope-cut + implementation planning. Extends the existing Stats service (already deployed at `stats.ishimura.lol` on ishimura).

**One-liner:** Grow Stats from an activity aggregator into the canonical "who and what" service. It already owns the event log; add user profile pages, achievement engine, gamerscore + rank tiers, taste profile computation (for Discover), and Now Playing aggregation. Absorbs concerns from the original crew-hub spec and the ishimura-profiles + ishimura-discover prototypes.

**Why:** Stats has the raw data. Every "who is this crew member?" question or "what would they enjoy?" query ends at Stats' event log. Splitting profile/achievement/taste concerns into separate services would just mean each of them re-derives the same primitives from the same DB.

## Guiding principles

- **Stats owns user data.** Event log, per-user aggregation, taste profiles, achievements, gamerscore, rank, Now Playing status.
- **UI concerns split cleanly.** Stats renders profile pages + achievement pages + roster. Homepage owns the nav widget (needs stable URL on the root domain). Bridge owns the admin console. Requests owns the Discover tab (consumes Stats' taste-profile API).
- **Retention-friendly derivations.** Profile/achievement/taste caches are derived from the event log and can always be rebuilt.
- **Existing dashboard stays.** The current `stats.ishimura.lol` overview UI is unchanged; profiles + achievements + roster are new pages, not a redesign of the existing dashboard.

## Non-goals

- Not a chat/messaging service (that lives in the homepage overlay - see the crew-hub restructure note)
- Not an authorization service (voidauth handles that)
- Not surfacing recommendations directly (that's Requests' Discover tab consuming Stats' API)
- Not replacing external stats providers (Last.fm scrobbles etc. still flow to their upstream; Stats just also captures them)

## Scope additions

Existing Stats has: event log across Jellyfin/Navidrome/BookLore/RomM/Rec Deck, per-user summary dashboard, retention/pruning, webhook receivers.

New scope this spec adds:

1. **Profile pages** at `/crew/<user>` - all-in-one profile view
2. **Roster** at `/crew/` - list of all users
3. **Achievement engine** - YAML-defined, periodic recheck, unlock tracking
4. **Gamerscore + ranks** - Dead Space-themed rank tiers based on total achievement points
5. **Taste profile computation** - genre affinity weights with exponential decay, negative signals, cross-media bridges
6. **Now Playing aggregation** - poll Jellyfin `/Sessions`, Navidrome subsonic, Hangar `/public/status`, Rec Deck live matches
7. **Recent activity feed** per user - already partially exists as a dashboard section; formalize as public API
8. **Public APIs** consumed by other services (Homepage's nav widget, Bridge, Refinery, Daily, Requests' Discover tab, Comms Officer bot)

## Data model additions

Alongside existing `events` table:

```sql
CREATE TABLE achievements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    points INTEGER DEFAULT 0,
    category TEXT NOT NULL,               -- video, music, games, books, cross, lifestyle, social
    parent_id TEXT,                       -- tiered achievement parent
    tier INTEGER DEFAULT 0,
    threshold REAL
);

CREATE TABLE user_achievements (
    username TEXT NOT NULL,
    achievement_id TEXT NOT NULL,
    unlocked_at TIMESTAMP,
    progress REAL DEFAULT 0,              -- 0.0-1.0 for locked-but-in-progress
    PRIMARY KEY (username, achievement_id)
);

CREATE TABLE user_scores (
    username TEXT PRIMARY KEY,
    gamerscore INTEGER DEFAULT 0,
    rank_title TEXT DEFAULT 'Maintenance Crew',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_taste_profiles (
    username TEXT NOT NULL,
    media_type TEXT NOT NULL,             -- movie, show, anime, song, book, game
    genre TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0,       -- normalized 0.0-1.0 per media_type
    play_count INTEGER DEFAULT 0,
    last_played TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, media_type, genre)
);

CREATE TABLE user_seeds (
    username TEXT NOT NULL,
    source TEXT NOT NULL,                 -- "jellyfin", "navidrome", "romm", "booklore"
    media_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    external_id TEXT,                     -- resolved tmdb:12345 etc
    metadata TEXT,                        -- JSON: genres, artist, etc
    played_at TIMESTAMP NOT NULL,
    play_count INTEGER DEFAULT 1,
    engagement_score REAL,                -- play_count * completion * recency_decay
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, source, item_id)
);
CREATE INDEX idx_seeds_user_type ON user_seeds(username, media_type);

CREATE TABLE now_playing_cache (
    username TEXT NOT NULL,
    source TEXT NOT NULL,                 -- "jellyfin", "navidrome", "hangar", "games"
    title TEXT,
    detail TEXT,                          -- artist, episode, wave number, opening move, etc.
    poster_url TEXT,
    started_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, source)
);
```

## Profile page (`/crew/<user>`)

Single-scroll layout, cross-source data:

**Header:** avatar + username + rank title (from `user_scores.rank_title`) + gamerscore + member-since date. Now Playing badge if `now_playing_cache` has a row.

**Stats grid:** ~12 cards. Games (Chess Elo, wins, tickets, arbiter, blackjack, slots) + Media (watch time, songs, ROMs, books, reading time, rec deck plays). Same visual as existing dashboard cards.

**Recent achievements:** last 5 unlocked with dates.

**Achievement showcase:** user picks 6 favorites to highlight. Grid of icons + names + points.

**Recent activity feed:** last 20 events. `3h ago :: watched Alien on Jellyfin`, `5h ago :: won a chess game vs kendra`, etc.

**Links:** full achievements page (`/crew/<user>/achievements`), leaderboards, avatar customize (if self-view).

**Access:** any voidauth user can view any profile. Self-view unlocks additional edit controls (showcase picker, avatar customize link).

## Roster (`/crew/`)

List of all users with mini cards:

- Avatar + username + rank
- Gamerscore
- Online/away/offline dot (based on `now_playing_cache` presence + last activity)
- Current activity ("Watching Alien" / "Listening to Deftones" / "Idle")

Sort options: alphabetical, last-active, gamerscore descending. MVP defaults to gamerscore.

## Achievement engine

YAML config loaded at startup from `/etc/stats/achievements.yaml`. Background job every 30 min queries the event log, checks conditions, unlocks new achievements + updates progress on tiered ones.

Achievement definition:

```yaml
achievements:
  - id: video_hours_100
    name: "Century Viewer"
    description: "Watched 100 hours of video"
    icon: monitor
    points: 50
    category: video
    condition:
      source: jellyfin
      metric: total_duration_hours
      threshold: 100
    tiers:
      - { threshold: 100,  name: "Century Viewer",   points: 50 }
      - { threshold: 500,  name: "Dedicated Viewer", points: 100 }
      - { threshold: 1000, name: "Marathon Runner",  points: 200 }

  - id: binge_day
    name: "Binge Watcher"
    points: 50
    category: video
    condition:
      source: jellyfin
      metric: max_daily_hours
      threshold: 10

  - id: streak_7
    name: "Weekly Streak"
    points: 25
    category: lifestyle
    condition:
      metric: max_daily_streak
      threshold: 7
    tiers:
      - { threshold: 7,   name: "Weekly Streak",    points: 25 }
      - { threshold: 30,  name: "Monthly Streak",   points: 75 }
      - { threshold: 100, name: "Centurion Streak", points: 200 }

  - id: crew_bond
    name: "Crew Bond"
    description: "Watched the same movie as another crew member within 24h"
    points: 30
    category: social
    condition:
      metric: crew_bond_events
      threshold: 1
```

Categories: `video`, `music`, `games`, `books`, `cross`, `lifestyle`, `social`.

Sample achievement types worth authoring on ship:

- Threshold: watched N hours, played N songs, read N books
- Streak: active every day for 7/30/100 days
- Diversity: watched content in 10 genres, played games on 5 platforms
- Repeat: same song 50 times, same movie 3 times
- Time-of-day: 50%+ activity between 10PM-4AM ("Night Owl")
- Cross-service: active in 4/6 services in a week
- Social: watched same movie as another user within 24h ("Crew Bond"), 50%+ genre overlap ("Taste Match"), 3+ users streaming simultaneously ("Party Mode")

### Rank tiers

| Points | Rank |
|---|---|
| 0-99 | Maintenance Crew |
| 100-499 | Systems Technician |
| 500-999 | Flight Specialist |
| 1000-2499 | Senior Engineer |
| 2500-4999 | Bridge Officer |
| 5000-9999 | Deck Commander |
| 10000+ | Captain |

### Unlock side-effects

New achievement unlock triggers:

- Ntfy push to the user's subscribed topic
- POST to Comms Officer Discord bot's `/event` endpoint (bot cross-posts to `#recovered-logs` or `#achievements`)
- Achievement-badge on next page load across ishimura services via nav widget

## Taste profile engine

Absorbed from ishimura-discover. Rebuilds per user every 30 min.

**Genre weights** use exponential time decay:

```
DECAY_HALF_LIFE_DAYS = 60
weight(media_type, genre) = SUM(0.5 ^ (days_ago / 60)) for each event
Then normalize within media_type so weights sum to 1.0
```

**Negative signals:** completion < 20% applies a negative weight (`-0.5 * decay_factor`) instead of positive. Dampens rejected genres.

**Seed selection:** 8 best seeds per media_type from last 90 days, ranked by `play_count * completion_ratio * recency_decay`. Populates `user_seeds`.

**Cross-media bridge table** (config-level, not per-user):

```python
CROSS_MEDIA_BRIDGES = {
    ("movie", "Animation"): [("music", "Anime"), ("music", "J-Pop")],
    ("music", "Jazz"):      [("movie", "Music"), ("movie", "Documentary")],
    ("movie", "Science Fiction"): [("book", "Science Fiction"), ("game", "Sci-Fi")],
    ("book", "Fantasy"):    [("game", "RPG"), ("movie", "Fantasy")],
    ("game", "RPG"):        [("book", "Fantasy"), ("movie", "Fantasy")],
    ("movie", "Horror"):    [("game", "Horror"), ("book", "Horror")],
}
```

Used by Requests' Discover tab to fetch cross-media candidates.

## Now Playing aggregation

Poll every 30s per source:

- **Jellyfin** `/Sessions` API - active video streams (title + user + elapsed/remaining)
- **Navidrome (or successor)** Subsonic `getNowPlaying`
- **Hangar** `/public/status` for game server presence
- **Rec Deck / games** live match state via existing `/api/live` endpoint

Populate `now_playing_cache` table. Stale rows (updated > 5 min ago) get pruned.

Expose at `/api/now-playing/<username>` for other services to consume.

## Public APIs

Stats becomes an API server for other services. Existing dashboard UI keeps its private routes; new public APIs (localhost-only, no voidauth check):

| Route | Consumer | Description |
|---|---|---|
| `GET /api/user/<username>/summary` | Homepage widget, Comms Officer | Existing dashboard summary |
| `GET /api/user/<username>/recent?limit=N` | Homepage nav widget | Recent activity feed |
| `GET /api/user/<username>/achievements` | Homepage, Comms Officer | List of unlocked + progress |
| `GET /api/user/<username>/gamerscore` | Homepage nav widget | Rank + score |
| `GET /api/user/<username>/taste-profile` | Requests Discover tab | Genre weights + seeds |
| `GET /api/user/<username>/seeds?media_type=X` | Requests Discover tab | Seed items for "because you watched X" |
| `GET /api/now-playing/<username>` | Homepage nav widget, Daily | Current activity |
| `GET /api/now-playing` | Daily "Now streaming aboard" widget | All active users |
| `GET /api/leaderboard[/<category>]` | Homepage, Daily | Ranked lists |
| `GET /api/crew` | Homepage roster | All users + rank + score |
| `GET /api/achievements` | Homepage, Comms Officer | All achievement definitions |
| `POST /api/achievement-showcase` | Self-view profile | Update showcased achievements |

All localhost-only; auth exemption pattern already used by `games:5001/api/user/<user>/dossier`.

## UI surfaces

New pages served by stats.ishimura.lol:

- `/crew/` - roster
- `/crew/<user>` - profile page
- `/crew/<user>/achievements` - full achievements list with progress
- `/leaderboard` - overall + per-category rankings
- `/leaderboard/weekly` - resets weekly for competition

Existing pages unchanged: overview dashboard, per-user dashboard, admin.

## Extension phases

### Phase 1 - Achievement engine + gamerscore (1 week)

- YAML loader + achievements table
- Background scorer job (30 min)
- Rank tier calculation
- `/crew/<user>` profile page (initial: header + stats grid + recent activity)
- `/crew/<user>/achievements` full list page
- New public APIs for gamerscore + achievements
- Ntfy on new unlock

### Phase 2 - Roster + taste profile + Now Playing (1 week)

- `/crew/` roster page
- Taste profile computation job (30 min)
- `user_taste_profiles` + `user_seeds` tables
- Public API for taste profile + seeds
- Now Playing collector + cache
- `/api/now-playing/*` endpoints

### Phase 3 - Leaderboards + polish (3-5 days)

- `/leaderboard` + `/leaderboard/weekly` pages
- Achievement showcase picker on self-view profile
- Cross-post to Comms Officer bot on unlock
- Nav widget badge integration (updates via widget's existing polling)

### Phase 4 - Weekly/monthly challenges (3-5 days)

- `challenges` + `user_challenges` tables
- Admin UI to author time-limited challenges
- Auto-generated challenge suggestions ("Horror Week", "Album Explorer")
- Cross-post to Daily's newsletter section

### Phase 5 - Social achievements (3-5 days)

- Crew Bond, Taste Match, Party Mode detection queries
- Correlation across users' event logs
- Nightly job

## Ties into

- [[requests]] - Requests' Discover tab consumes `/api/user/<user>/taste-profile` + `/api/user/<user>/seeds`
- [[homepage]] - Homepage's nav widget consumes gamerscore/achievement/now-playing APIs
- [[daily]] - Daily's "Now streaming aboard" + calendar/classifieds consume Stats' APIs
- [[bridge]] - Bridge doesn't overlap; profiles are user-facing, Bridge is admin-facing
- [[comms officer]] - Discord bot consumes achievement unlock events + Now Playing
- [[crew-hub]] - This spec supersedes crew-hub's Phase 2/3 (profile + achievements + avatars); crew-hub's Phase 1 (nav widget + messaging) moves to the homepage overlay

## Non-goals (revisited)

- Not the source of truth for identity (voidauth is)
- Not the auth checker (voidauth-forwardauth is)
- Not a real-time WebSocket surface for Now Playing (30s polling is enough)
- Not a chat/messaging service (homepage overlay owns that)
- Not surfacing recommendations directly (Requests' Discover tab does that using Stats' APIs)

## Open questions

- **Taste profile freshness** - 30 min rebuild feels right, but for very active users the cost is nontrivial. Consider incremental update on new event.
- **Now Playing polling load** - 30s * 4 sources * N users = N*8 API calls/min. Fine at 10 users, watch at 100.
- **Achievement YAML hot-reload** - do we restart Stats on YAML change or watch the file? Watch probably.
- **Seed engagement scoring** - `play_count * completion * recency_decay` is a first guess. May need tuning per media_type.
- **Discord bot integration timing** - Bot's `/event` endpoint doesn't exist yet; wire it up when the bot ships.

## Requests service - Discover tab addition

The Requests service already exists at requests.ishimura.lol and handles the wanted-list state (pending → approved → completed). This absorbs ishimura-discover's UI concerns as a new tab in the existing service, powered by Stats' taste-profile API.

**New route:** `/discover` in requests.ishimura.lol

**What it does:**

1. On page load, fetch `/api/user/<self>/taste-profile` and `/seeds` from Stats
2. For each seed, fetch candidate recommendations from external APIs (TMDB, Last.fm, OpenLibrary, IGDB)
3. Score candidates against the user's taste profile (genre affinity + provider rating + seed relevance + novelty + diversity + cross-media bonus)
4. Group into sections: "Because you watched X", "New in your genres", "Trending in <genre>", "Cross-media discovery"
5. Render as horizontal poster carousels
6. Per-card actions: **request** (adds to wanted list - the existing requests flow), **save/bookmark**, **dismiss**, **share with @user**
7. Mark items already in library with an "In Library" badge (skip request button)

**Additions to requests DB:**

```sql
CREATE TABLE discover_dismissed (
    username TEXT NOT NULL,
    rec_item_id TEXT NOT NULL,
    dismissed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, rec_item_id)
);

CREATE TABLE discover_saved (
    username TEXT NOT NULL,
    rec_item_id TEXT NOT NULL,
    title TEXT NOT NULL,
    media_type TEXT NOT NULL,
    poster_url TEXT,
    metadata TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, rec_item_id)
);

CREATE TABLE discover_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user TEXT NOT NULL,
    to_user TEXT NOT NULL,                -- "*" = shared with everyone
    rec_item_id TEXT NOT NULL,
    title TEXT NOT NULL,
    media_type TEXT NOT NULL,
    poster_url TEXT,
    note TEXT,
    seen BOOLEAN DEFAULT 0,
    shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE discover_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_item_id TEXT NOT NULL,
    source_media_type TEXT NOT NULL,
    rec_item_id TEXT NOT NULL,
    rec_provider TEXT NOT NULL,           -- tmdb, lastfm, openlibrary, igdb
    rec_media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    year TEXT,
    overview TEXT,
    poster_url TEXT,
    genres TEXT,                          -- JSON array
    rating REAL,
    extra_data TEXT,                      -- JSON: provider-specific
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_item_id, rec_item_id)
);
CREATE INDEX idx_disc_cache_source ON discover_cache(source_item_id);
```

**Scoring algorithm** (adapted from ishimura-discover):

```
score = 0.40 * genre_affinity              # from taste profile
      + 0.15 * provider_rating / 10        # TMDB/etc rating
      + 0.20 * seed_relevance              # recency + play count of seed
      + 0.05 * novelty_bonus               # if unfamiliar genre
      + 0.10 * cross_media_bonus           # if different media_type than seed
      - 0.05 * genre_saturation_penalty    # if section already has 3+ same-genre
```

**Genre cooldown:** 3+ dismissals of a genre in 7 days → suppress genre by 50% weight for scoring. Applied at scoring time from `discover_dismissed`, not persisted in profile.

**"Already in library" detection:** Cross-reference against Refinery's `items` table + Jellyfin API. Cached 30 min.

**Offline fallback:** External API failure → serve stale `discover_cache` entries. Never discard stale until successfully replaced.

**Sharing:** "Share with @user" creates a `discover_shares` row visible to the recipient. When they act on it (request/dismiss/save), the share is marked `seen`. Also cross-posts to Comms Officer bot for "MaxwellPayne shared Blade Runner with you".

**Requests service phases:**

1. Discover tab MVP (2-3 evenings) - reads Stats' taste profile, fetches TMDB/Last.fm candidates, renders one section per seed
2. Full provider coverage (3-5 days) - OpenLibrary + IGDB + cross-media bridge sections
3. Actions + library-awareness (3-5 days) - dismiss, save, request (existing flow), library check
4. Social (2-3 evenings) - share with user, shares inbox on same page

## Sops secrets needed

Adds to sops for the Discover tab:

- `requests/tmdb_read_access_token` (already exists as `tmdb/read_access_token`)
- `requests/lastfm_api_key` (already exists as `beets/lastfm_api_key`)
- `requests/igdb_client_id` + `requests/igdb_client_secret` (already exist as `romm/igdb_*`)

All borrow from existing keys.
