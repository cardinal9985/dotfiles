# ROMM Replacement - ROM Library + Emulator (`roms.ishimura.lol`)

**Status:** design 2026-07-09. Replaces ROMM with a themed library + EmulatorJS play-in-browser + refinery integration.

**One-liner:** Self-hosted ROM library manager that shares refinery's already-existing IGDB integration + platform taxonomy + hash cache, adds per-user save states + play-in-browser via EmulatorJS, and shows RetroAchievements progress.

**Why:** ROMM is fine but a whole Rails + Postgres + Redis stack for what's essentially "file list + metadata + saves". Refinery already does the intake, hashing, and IGDB lookup. This service is the frontend + play surface.

## Non-goals

- Not a downloader (ROMs come in via refinery)
- Not a full emulator (EmulatorJS handles per-platform cores in browser)

## Architecture

- Flask on ishimura, port `5015`, nix module `modules/nixos/ishimura/roms.nix`
- Persistence `/persist/roms/roms.db` for user data (saves, states, favorites, achievements cache)
- ROM files at `/mnt/storage/media/roms/{platform}/` (existing structure preserved, refinery already writes here)
- Voidauth-forwardauth for all routes
- EmulatorJS bundled via nix derivation from `github.com/EmulatorJS/EmulatorJS` release
- netplay orchestration 

## Data model

Refinery's `items` table already has ROM entries with hashes + IGDB + platform. This service reads from refinery's DB (mounted read-only) rather than duplicating.

Own DB adds:

```sql
CREATE TABLE saves (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    rom_hash TEXT NOT NULL,          -- links to refinery items.meta_json.hashes.sha1
    slot INTEGER DEFAULT 0,          -- 0 = auto, 1-9 = numbered slots
    file_blob BLOB,                  -- save file bytes (usually small)
    save_type TEXT,                  -- "sram", "state", "memcard"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(username, rom_hash, slot, save_type)
);

CREATE TABLE play_sessions (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    rom_hash TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    duration_secs INTEGER
);

CREATE TABLE favorites (
    username TEXT NOT NULL,
    rom_hash TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, rom_hash)
);

CREATE TABLE retroachievements_cache (
    rom_hash TEXT PRIMARY KEY,
    ra_game_id INTEGER,
    achievements_json TEXT,          -- full RA achievement list
    fetched_at TIMESTAMP
);

CREATE TABLE user_ra_progress (
    username TEXT NOT NULL,
    rom_hash TEXT NOT NULL,
    unlocked_achievements TEXT,     -- JSON array of RA achievement ids
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, rom_hash)
);
```

## Features

- **Library browse** - grouped by platform, filter/search, poster grid + list view
- **Metadata from refinery** - title, developer, year, genre, cover, IGDB summary all read live from refinery's items table
- **Play in browser** - EmulatorJS with per-platform cores. Auto-detects platform from refinery, picks default core, loads ROM
- **Save states + SRAM** - per-user, per-slot, synced across devices. Uploaded from EmulatorJS on save, downloaded on load
- **Play sessions** - track play time per user per ROM; feeds stats
- **Favorites + Now Playing** - per-user favorites; publishes Now Playing to stats
- **RetroAchievements integration** - RA-hash lookup (RA uses different hashes than redump/no-intro), shows achievement list, tracks user progress via RA's API, awards ishimura achievements (via stats-extension) when RA milestones hit
- **Multi-disc + M3U support** - shows PS1/Saturn/PC-Engine CD games as single entries with disc-swap UI in EmulatorJS
- **Companion tab: Play with friends** - deep-link into intercom's session coordinator to spin up netplay
- **Import/export saves** - dump all saves for backup, restore from zip

## RetroAchievements

- User adds RA username in their profile (stored in stats' user prefs, not here)
- Background job every hour fetches RA API for each active user's progress
- Cache in `user_ra_progress`; feed new unlocks to stats-extension as achievements
- Cross-post big unlocks (100% completion, mastered) to Discord via Comms Officer

## Stages

1. **MVP library + metadata (3-5 days)** - browse, filter, read from refinery's items table
2. **EmulatorJS + saves (1 week)** - play-in-browser, save state upload/download, per-user isolation
3. **Play sessions + stats (2-3 days)** - track play time, feed stats events, Now Playing
4. **RetroAchievements (3-5 days)** - RA hash lookup, progress fetch, achievement cross-post
5. **Import from ROMM (3 days)** - one-shot migration of ROMM's user data (favorites, play history) into new schema

## Ties into

- [[refinery-arr]] - reads ROM library + metadata from refinery
- [[stats-extension]] - play sessions + RA achievements
- [[intercom]] - "play with friends" deep-links into session coordinator for netplay
- [[hangar]] - unrelated (hangar is native game servers, this is emulated console games)
- [[daily]] - Now Playing widget

## Open questions

- **Netplay** - EmulatorJS has experimental netplay support. If it works we could bypass intercom coordinator for simple cases. If janky, coordinator (via intercom) sets up voice channel + everyone loads the same ROM + syncs manually via LibreDGB or similar
- **Save conflict resolution** - if user plays on two devices without syncing, last-write-wins is dumb. Add auto-save-slot-cycling or force user to name save slots?
- **RA hash calculation** - RA uses per-platform hash algorithms (not just sha1 of file). Need to implement each. Reference: [RA docs](https://docs.retroachievements.org/developer-docs/game-identification.html)
