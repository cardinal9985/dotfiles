# Music Service - Navidrome Replacement (`music.ishimura.lol`)

**Status:** design 2026-07-09. Replaces Navidrome with a fully Subsonic-compatible custom service. Radio stations + podcasts + fretboard integration all under one umbrella.

**One-liner:** Self-hosted multi-user music streaming with full Subsonic API compatibility (native mobile apps keep working), custom Ishimura-themed web UI, radio station browsing, podcast subscriptions, and instrument tab library integration (fretboard folds in as `/instruments`).

**Why:** Navidrome is great but not themable to the ship aesthetic. Same DIY pattern as refinery/hangar. Subsonic compat is non-negotiable so DSub/Substreamer/Symfonium keep working.

## Non-goals

- Not a Spotify replacement with recommendation editorial - use stats' taste profile instead
- Not a DJ/mixing tool - just library streaming
- Not YouTube Music import

## Architecture

- Flask + Subsonic API blueprint on ishimura, port `5014`, nix module `modules/nixos/ishimura/music.nix`
- Persistence `/persist/music/music.db` + audio at `/mnt/storage/media/music/` (existing structure preserved)
- Voidauth OIDC for web UI; Subsonic-API tokens for mobile apps (per-user password stored hashed)
- Streams audio via Traefik `X-Accel-Redirect` / `X-Sendfile` so Flask doesn't touch big files
- FluidR3 GM soundfont for fretboard playback (from `2026-07-09-fretboard-design.md`)

## Data model

```sql
CREATE TABLE artists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    sort_name TEXT,
    mbid TEXT,                  -- MusicBrainz ID
    cover_local TEXT,
    biography TEXT,
    listens INTEGER DEFAULT 0
);

CREATE TABLE albums (
    id INTEGER PRIMARY KEY,
    artist_id INTEGER REFERENCES artists(id),
    title TEXT NOT NULL,
    year INTEGER,
    genre TEXT,
    mbid TEXT,
    cover_local TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tracks (
    id INTEGER PRIMARY KEY,
    album_id INTEGER REFERENCES albums(id),
    artist_id INTEGER REFERENCES artists(id),
    title TEXT NOT NULL,
    track_no INTEGER,
    disc_no INTEGER DEFAULT 1,
    duration_secs INTEGER,
    file_path TEXT NOT NULL,
    file_format TEXT,
    bitrate_kbps INTEGER,
    replay_gain REAL,
    lyrics_synced TEXT,         -- LRC
    lyrics_plain TEXT
);
CREATE INDEX idx_tracks_album ON tracks(album_id);

CREATE TABLE playlists (
    id INTEGER PRIMARY KEY,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    public BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE playlist_tracks (
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
    position INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (playlist_id, track_id)
);

CREATE TABLE listens (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    track_id INTEGER REFERENCES tracks(id),
    listened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_played INTEGER,      -- seconds actually played
    device TEXT
);

CREATE TABLE radio_stations (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    stream_url TEXT NOT NULL,
    homepage_url TEXT,
    genre TEXT,
    country TEXT,
    logo_url TEXT,
    favorites_count INTEGER DEFAULT 0
);

CREATE TABLE podcast_feeds (
    id INTEGER PRIMARY KEY,
    feed_url TEXT UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    cover_local TEXT,
    added_by TEXT,
    last_fetched_at TIMESTAMP,
    fetch_interval_hours INTEGER DEFAULT 6
);

CREATE TABLE podcast_episodes (
    id INTEGER PRIMARY KEY,
    feed_id INTEGER REFERENCES podcast_feeds(id) ON DELETE CASCADE,
    title TEXT,
    description TEXT,
    audio_url TEXT NOT NULL,
    local_path TEXT,              -- if downloaded
    duration_secs INTEGER,
    published_at TIMESTAMP,
    downloaded_at TIMESTAMP
);
```

## Features

- **Subsonic API** (v1.16+) at `/rest/*` - streaming, playlists, browsing, search, star/rating, scrobbling. Full spec: [subsonic.org](https://subsonic.org/pages/api.jsp)
- **Custom web UI** in ship theme - browse, play, queue, playlists, lyrics, discography
- **Radio** - browse radio stations (seeded from radio-browser.info's free API), favorite stations, per-user history. Streams `.m3u`/`.pls`/direct MP3 URLs transparently
- **Podcasts** - subscribe to RSS/Atom feeds, auto-download new episodes into `/mnt/storage/media/podcasts/{feed}/`, tracks per-episode listened state, downloads pruned after N days played
- **Fretboard as `/instruments`** - full absorption of the fretboard design; tabs, metronome, jam-with-song (overlay tab on currently-playing track from music library)
- **Playlists** - private + public, standard M3U export/import
- **Scrobbling** - forwards to Last.fm + ListenBrainz + stats webhook (all optional per-user)
- **ReplayGain-aware playback**
- **Synced lyrics** (LRC) with karaoke-style highlight
- **Multi-user** - per-user library visibility isn't the goal (household shares one library), but playlists, favorites, scrobbles, listens are per-user
- **Media scanning** - inotify watcher on `/mnt/storage/media/music/` + full rescan cron; new music from refinery auto-appears
- **Search** - full-text across artists/albums/tracks/lyrics

## Fretboard integration (folds `2026-07-09-fretboard-design.md`)

- Tabs live at `/mnt/storage/media/tabs/{artist}/{title}.{ext}`
- Match on `artist + title` fuzzy so playing an album from music library surfaces "3 tabs available" link if fretboard has matching tabs
- Jam mode: pick a tab, pick a track (must match tempo), synced playback with metronome + fretboard overlay
- Fretboard reader + metronome + Songsterr/jTab imports all remain intact

Once music-service ships, `tabs.ishimura.lol` becomes a 301 redirect to `music.ishimura.lol/instruments`.

## Stages

1. **Subsonic API + scanner (1-2 weeks)** - schema + scanner + Subsonic endpoints; existing Subsonic clients work
2. **Web UI + playlists (1 week)** - ship-themed browse/play/queue/lyrics
3. **Radio (3-5 days)** - radio-browser integration, favorites, station player
4. **Podcasts (1 week)** - feed subscribe, background fetch, episode player, listened state
5. **Fretboard fold-in (3-5 days)** - migrate fretboard code into `/instruments`, wire jam-mode against library
6. **Migration from Navidrome (2-3 days)** - one-shot import of Navidrome's SQLite (users, playlists, favorites) into new schema

## Ties into

- [[refinery-arr]] - music intake feeds directly into music.db instead of just dropping files
- [[stats-extension]] - listen events feed taste profile + achievements + Now Playing
- [[fretboard]] - absorbed
- [[vtt]] - VTT scene playlists use this service's Subsonic API for background music
- [[daily]] - "Now streaming aboard" widget consumes Now Playing

## Open questions

- Kobo-style device sync for offline listening on phones - Subsonic clients handle their own offline mode, probably enough
- Multi-user library isolation - are we ever going to want per-user libraries? Design allows it (username column on listens/playlists/scrobbles) but scanner assumes single shared library
