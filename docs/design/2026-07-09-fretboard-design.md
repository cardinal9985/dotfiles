# Fretboard - Guitar Tab Manager (nixos-native redesign)

**Status:** design 2026-07-09. Rebuild of the earlier Docker-based fretboard prototype as a nixos-native Flask service that eventually merges into the custom Navidrome successor's `/instruments` surface.

**One-liner:** Self-hosted guitar tab manager + practice tools. Tab library (GP/GPX/GP5/MusicXML/MIDI), AlphaTab renderer with playback, visual composer, Songsterr + jTab imports, standalone metronome. Nix-declared derivation, systemd unit under `music` user, sops secrets for the Songsterr scraper (if it needs auth), voidauth-gated.

**Why nixos-native rather than porting the Docker container:** Every other custom app on the fleet is nix-native (refinery, requests, stats, games, hangar). Docker duplicates the deploy/perm/secret dance we already solved once in nix. Second time doing "port a Docker prototype to nixos" so pattern is well-established.

**Long-term destination:** Fold into the custom Navidrome successor as an "Instruments" tab. Same shared user + voidauth + theming shell. Tabs, metronome, jam-with-song, playback-with-guitar-notation-overlay all live under the umbrella of "the ishimura music service" rather than a standalone subdomain.

## Guiding principles

- **Nix-declared derivation.** No custom Docker image, no runtime pip install.
- **AlphaTab does the rendering.** Don't reinvent tab rendering; use the JS library.
- **Web-only.** No mobile app, no desktop client. Browser + fretboard = enough.
- **Practice tools first, composition second.** Tab library + player + metronome are the daily-driver features. Visual composer is nice-to-have.
- **Local audio.** Use FluidR3_GM.sf2 SoundFont (open license, ~150MB) for playback. No cloud audio calls.

## Non-goals

- Not a lesson platform (no curriculum, no progress tracking beyond simple last-played)
- Not a full DAW (no multi-track recording)
- Not YouTube integration (URL-to-tab AI stuff)
- Not tabs for other instruments beyond guitar/bass (no piano roll, no drum notation)

## Architecture

### Hosting

Flask app on ishimura:

- Port `5012` (adjust to fit existing port allocation)
- Nix module at `modules/nixos/ishimura/fretboard.nix`
- Runs as `music` user (or its own `fretboard` user, TBD when we spec the navidrome successor)
- Persistence at `/persist/fretboard/` for SQLite + user-uploaded tabs
- Tab library filesystem at `/mnt/storage/media/tabs/{artist}/{title}.{ext}` mirroring the music library pattern
- FluidR3 SoundFont bundled as a nix data derivation (fetched once, checksum-pinned)

Optional destination: mount at `music.ishimura.lol/instruments/` as an internal path of the navidrome successor when that ships. For MVP, standalone at `tabs.ishimura.lol`.

### Frontend

- AlphaTab.js loaded from CDN + local vendored fallback
- Fretboard SVG rendered client-side
- Web Audio API metronome (no server-side audio)
- CRT terminal theme matching homepage aesthetic (starfield, monospace, scanlines)

### Backend

Small Flask app. Handlers:

- Library index (list of artists → tabs)
- Upload endpoint (accepts GP/GPX/GP5/MusicXML/MIDI, drops into artist folder)
- Tab detail (renders AlphaTab viewer with metadata)
- Songsterr search (proxy their public search API + download tab)
- jTab import (parse Obsidian markdown with `$string.fret` notation)
- Metronome page (client-side only, backend just serves the HTML)
- Delete/rename endpoints (admin-gated)

## Data model

```sql
CREATE TABLE tabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,             -- absolute path under /mnt/storage/media/tabs
    file_format TEXT NOT NULL,           -- gp, gpx, gp5, xml, mid
    tuning TEXT,                         -- "EADGBE" (parsed from GP if available)
    difficulty INTEGER,                  -- 1-5 (user-set or Songsterr-provided)
    tempo INTEGER,                       -- BPM, parsed from GP
    duration_secs INTEGER,               -- parsed from GP
    tags TEXT,                           -- JSON array
    cover_local TEXT,                    -- optional album/artist artwork
    imported_from TEXT,                  -- "manual", "songsterr", "jtab"
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_played_at TIMESTAMP,
    play_count INTEGER DEFAULT 0
);
CREATE INDEX idx_tabs_artist ON tabs(artist);

CREATE TABLE user_tab_state (
    username TEXT NOT NULL,
    tab_id INTEGER NOT NULL REFERENCES tabs(id) ON DELETE CASCADE,
    favorite BOOLEAN DEFAULT 0,
    last_position REAL,                  -- seconds into the tab
    loop_start REAL,
    loop_end REAL,
    tempo_multiplier REAL DEFAULT 1.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, tab_id)
);

CREATE TABLE metronome_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    name TEXT NOT NULL,
    bpm INTEGER NOT NULL,
    time_sig_num INTEGER DEFAULT 4,
    time_sig_denom INTEGER DEFAULT 4,
    subdivisions INTEGER DEFAULT 1,
    accents TEXT,                        -- JSON array of accented beat indexes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Features

### Tab library

- Grid layout: artist folders → individual tabs
- Filter/search by artist, title, tag, difficulty
- Upload form for adding new tabs (GP/GPX/GP5/MusicXML/MIDI)
- Rename + tag + delete on tab detail page
- Cover art auto-fetched from Last.fm / MusicBrainz on artist folder create (optional, low priority)

### AlphaTab viewer

- Renders tab notation + fretboard diagram + score
- Playback with FluidR3 GM soundfont
- Track selection (guitar 1 / guitar 2 / bass / drums / etc from multi-track GP files)
- Tempo control (0.25x-2x)
- Looping (set A-B markers, loop between)
- Count-in (1-4 measures)
- Metronome tick option during playback
- Auto-scroll follows current beat
- Right-hand fingering hints toggle

### Visual composer

- Clickable fretboard SVG + score grid
- Live AlphaTab preview via generated alphaTex
- Save as GP-compatible file
- Not the primary use case - keep MVP-tier simple

### Songsterr import

- Search Songsterr's catalog via their public search API
- Download tab as alphaTex (their embed format)
- Save to artist folder + insert into `tabs` table
- If a track is behind Songsterr Plus (paywalled), show "PREMIUM ONLY" and skip
- Rate-limit: max 20 searches/hour per user (Songsterr's TOS)

### jTab import (Obsidian markdown)

- Parse Obsidian markdown files using [jTab plugin](https://github.com/davfive/obsidian-jtab) notation (`$string.fret`)
- Bulk import from an uploaded folder or a mounted path

### Standalone metronome

- Web Audio API, no server-side audio
- Tap tempo (space bar or click)
- Time signatures (3/4, 4/4, 5/4, 6/8, 7/8, 12/8, etc)
- Subdivisions (eighth, triplet, sixteenth)
- Accent patterns (which beats get louder tick)
- Preset save/load per user
- Standalone page + embedded in tab viewer

## Nix module skeleton

```nix
{ config, pkgs, ... }:

let
  # FluidR3 GM soundfont pinned + fetched via nix store
  fluidR3 = pkgs.fetchurl {
    url = "https://ftp.osuosl.org/pub/musescore/soundfont/FluidR3Mono_GM.sf3";
    sha256 = "0000000000000000000000000000000000000000000000000000";  # TBD
  };

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    flask-socketio
    guitarpro  # PyGuitarPro for GP/GPX parsing
    music21    # MusicXML/MIDI parsing
    requests
  ]);

  fretboard = pkgs.stdenv.mkDerivation {
    name = "fretboard";
    src = ../../../config/fretboard;
    dontUnpack = true;
    installPhase = ''
      mkdir -p $out
      cp -r $src/* $out/
      ln -s ${fluidR3} $out/static/FluidR3_GM.sf3
    '';
  };
in
{
  users.users.fretboard = {
    isSystemUser = true;
    group = "fretboard";
    home = "/persist/fretboard";
    description = "Fretboard guitar tab manager";
  };
  users.groups.fretboard = {};

  systemd.tmpfiles.rules = [
    "d /persist/fretboard             0755 fretboard fretboard -"
    "d /mnt/storage/media/tabs        0755 fretboard fretboard -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/fretboard"; user = "fretboard"; group = "fretboard"; mode = "0755"; }
  ];

  systemd.services.fretboard = {
    description = "Fretboard - guitar tab manager";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];
    environment = {
      FRETBOARD_DB_PATH    = "/persist/fretboard/fretboard.db";
      FRETBOARD_TABS_DIR   = "/mnt/storage/media/tabs";
      FRETBOARD_SOUNDFONT  = "${fluidR3}";
      PORT                 = "5012";
    };
    serviceConfig = {
      Type             = "simple";
      User             = "fretboard";
      Group            = "fretboard";
      WorkingDirectory = fretboard;
      ExecStart        = "${pythonEnv}/bin/python ${fretboard}/app.py";
      Restart          = "on-failure";
      RestartSec       = "5s";
    };
  };
}
```

Pangolin route mirrors existing services with voidauth-forwardauth middleware.

## Stages

### Stage 1 - MVP tab library (3 evenings)

- Nix module up
- SQLite schema + migrations
- Upload flow + library index
- AlphaTab viewer (basic playback, no looping/tempo)
- Standalone metronome page
- CRT theme matching homepage

Deliverable: `tabs.ishimura.lol` shows uploaded tabs, plays them, ticks a metronome.

### Stage 2 - Practice tools (2-3 evenings)

- Tempo control + looping in AlphaTab viewer
- Count-in
- Metronome-during-playback
- Per-user state (last position, favorite, loop markers)
- Metronome preset save/load

### Stage 3 - Imports (2-3 evenings)

- Songsterr search + download
- jTab import from Obsidian markdown
- Bulk folder import (walk a mounted path, add all GP files)

### Stage 4 - Composer + polish (3-5 days)

- Clickable fretboard SVG editor
- Live alphaTex preview
- Save as GP-compatible file
- Tag + rename + cover art
- Full-text search across library

### Stage 5 - Merge into music service (deferred)

- When the Navidrome successor ships, migrate to `music.ishimura.lol/instruments/`
- Share user/session/theming shell
- Retain standalone `tabs.ishimura.lol` as redirect for a grace period

## Integration points

- **Stats/achievements** - practice-session-length events; "played 30 min today" streak; "learned N tabs" tier
- **Navidrome successor** - long-term absorption target; jam-with-song feature (fretboard overlay on top of playing music)
- **Refinery** - if music intake ships tab discovery (e.g. downloading a tab bundle with an album), Refinery could stage tabs into `/mnt/storage/media/tabs`
- **Comms Officer** - Discord bot posts when someone learned a new song ("Maxwell completed 'Master of Puppets' after 47 tries")

## Data sources

| Source | Access | Purpose |
|---|---|---|
| Songsterr Search API | public + rate-limited | Tab discovery + download |
| FluidR3 GM SoundFont | one-time nix fetch | Playback audio |
| AlphaTab.js | CDN + local vendored | Tab rendering |
| PyGuitarPro | pip / nix | GP/GPX/GP5 parsing |
| music21 | pip / nix | MusicXML/MIDI parsing |
| jTab (Obsidian plugin format) | markdown parser | Obsidian import |

## Ties into

- [[music-service]] (future navidrome successor) - long-term absorption
- [[stats-extension]] - practice-session events
- [[refinery-arr]] - tab bundle intake path
- [[comms officer]] - Discord posts on song-learned milestones
