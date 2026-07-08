# Refinery - Arr-Stack Replacement Design

**Status:** design brainstormed 2026-07-09, ready for scope-cut + implementation planning. Extends the existing Refinery service (already deployed at `refinery.ishimura.lol` on ishimura).

**One-liner:** Grow Refinery from a media intake/tagging tool into a full Radarr/Sonarr/Readarr/Lidarr replacement. One instance manages every library folder on `/mnt/storage/media/`, handles media that isn't on any external database, provides wanted lists + list sync + release calendar + release-day ntfy, and integrates with Refinery's existing approve/import pipeline.

**Why:** Refinery already handles media intake for music/video/book/game with hash lookups + IGDB + TMDB and library moves. Adding "wanted list" + "release calendar" + "monitored series" + list sync grows it into the full arr-stack replacement without introducing another service that needs its own DB, its own metadata cache, its own approve flow. All the intake code exists; wanted/calendar is additive.

## Guiding principles

- **Refinery already owns the intake + library pipeline.** Wanted list + calendar plug into that pipeline; they don't own their own separate flow.
- **Multi-library out of the box.** Existing per-media-type target folders (music/movies/anime-movies/documentaries/short-films/fan-edits/shows/anime-shows/documentary-shows/books/roms) become named "libraries" with per-library naming templates + provider preferences.
- **Handle media that isn't on any database.** Fan edits and obscure content should be first-class - manual metadata entry with no provider required.
- **Release calendar filtered to actual interest.** Not a firehose of every TMDB release. Only wanted-list items + monitored series.
- **Requests → Wanted → Import is one flow.** A request submitted at requests.ishimura.lol adds to Refinery's wanted list; when the file lands and is approved, request auto-closes.

## Non-goals

- Not a downloader (slskd + qBittorrent + jdownloader stay separate)
- Not a subtitle-generation engine (OpenSubtitles fetch only)
- Not a duplicate deleter without human confirmation (flag + suggest, don't auto-delete)
- Not a public-facing service (voidauth admins group required)

## Scope additions on top of current Refinery

Existing Refinery handles: intake queue, hash/DAT lookup for games, TMDB/IGDB/OpenLibrary/Bandcamp/Discogs/Last.fm metadata enrichment, media approve/reject/reprocess flow, library moves with per-type naming.

New scope this spec adds:

1. **Library definitions** - explicit per-folder config (name, path, media_type, folder/file templates, default provider) instead of hardcoded per-type folders
2. **Wanted list** - track media you plan to acquire but don't have yet
3. **List sync** - import wanted items from Trakt / IMDB / TMDB lists (one-time or periodic)
4. **Release calendar** - upcoming movies + TV episodes + game releases filtered to wanted + monitored
5. **Monitored series** - flag existing shows so new episodes auto-flow through refinery
6. **Requests bridge** - reads requests.ishimura.lol DB, one-click add request to wanted list, auto-close on import
7. **OpenSubtitles integration** - fetch subs for imported video
8. **Extras management** - Jellyfin-compatible `Behind The Scenes/`, `Deleted Scenes/`, `Featurettes/`, `Interviews/`, `Trailers/` subfolders on approve
9. **Trailer downloads** - yt-dlp from TMDB YouTube trailer URLs
10. **Duplicate + upgrade detection** - flag duplicate copies + higher-quality replacements in downloads
11. **Storage stats** - per-library disk usage, format/codec breakdown, NFS capacity
12. **Health dashboard** - status of adjacent services (Jellyfin, Navidrome/successor, RomM, BookLore, qBittorrent, slskd)
13. **Naming template editor** - live preview UI for editing per-library templates
14. **Bulk rename** - apply new template to existing library

## Data model additions

Alongside existing `items`, `tracks`, and processing tables, add:

```sql
CREATE TABLE libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,           -- "films", "anime-films", "documentary-shows"
    name TEXT NOT NULL,                  -- "Films", "Anime Movies"
    path TEXT NOT NULL,                  -- "/mnt/storage/media/movies"
    media_type TEXT NOT NULL,            -- "movie", "series", "music", "book", "game"
    folder_template TEXT NOT NULL,       -- "{title} ({year}) [{provider}id-{id}]"
    file_template TEXT NOT NULL,         -- "{title} ({year}) [{provider}id-{id}] - [{source}-{resolution}][{audio}][{codec}]-{group}"
    season_template TEXT DEFAULT 'Season {season:02d}',
    default_provider TEXT DEFAULT 'tmdb', -- tmdb, imdb, tvdb, ifdb, anilist, none
    monitored BOOLEAN DEFAULT 0,          -- auto-check for new episodes
    enabled BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wanted (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL REFERENCES libraries(id),
    title TEXT NOT NULL,
    year INTEGER,
    media_type TEXT NOT NULL,             -- "movie", "series", "music", "book", "game"
    tmdb_id INTEGER,
    imdb_id TEXT,
    tvdb_id INTEGER,
    igdb_id INTEGER,
    anilist_id INTEGER,
    priority INTEGER DEFAULT 5,           -- 1-10
    notes TEXT,
    added_by TEXT,                        -- voidauth username
    request_id INTEGER,                   -- FK to requests.db if sourced from a request
    status TEXT DEFAULT 'wanted',         -- wanted, importing, imported, dismissed
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    imported_at TIMESTAMP
);
CREATE INDEX idx_wanted_status ON wanted(status);
CREATE INDEX idx_wanted_priority ON wanted(status, priority DESC);

CREATE TABLE list_syncs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                   -- "Trakt Watchlist", "My IMDB Sci-Fi"
    kind TEXT NOT NULL,                   -- "trakt", "imdb", "tmdb"
    url_or_id TEXT NOT NULL,              -- list URL, trakt username, tmdb list id
    sync_interval_hours INTEGER DEFAULT 24,
    library_id INTEGER REFERENCES libraries(id),
    last_synced_at TIMESTAMP,
    last_sync_result TEXT,
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE monitored_series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL REFERENCES libraries(id),
    title TEXT NOT NULL,
    tvdb_id INTEGER,
    tmdb_id INTEGER,
    last_checked_at TIMESTAMP,
    next_episode_air_date DATE,
    next_episode_snn INTEGER,
    next_episode_enn INTEGER,
    active BOOLEAN DEFAULT 1
);

CREATE TABLE release_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,                 -- "wanted:42", "monitored:7"
    media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    release_date DATE NOT NULL,
    tmdb_id INTEGER,
    tvdb_id INTEGER,
    season_no INTEGER,
    episode_no INTEGER,
    episode_title TEXT,
    poster_url TEXT,
    notified BOOLEAN DEFAULT 0,           -- ntfy pushed at 24h?
    UNIQUE(source, release_date, season_no, episode_no)
);
CREATE INDEX idx_calendar_date ON release_calendar(release_date);
```

Existing `items` table gains an optional FK column `wanted_id` for the wanted item that was fulfilled, so the auto-close chain works.

## New sections in the Refinery UI

Existing surfaces: Queue (in-flight items), Library browse (per-media-type), Approve/Reject/Reprocess, Settings.

New tabs:

### Wanted (`/wanted`)

- Grid + list toggle
- Filters: media_type, library, priority, added_by, status
- Actions per item: change priority, add notes, dismiss, mark-as-satisfied (manual override), delete
- Add-item button: search TMDB/IGDB/OpenLibrary + attach to library
- Bulk import from paste (one title per line, auto-search per provider)
- Auto-highlight when a queue item matches a wanted entry

### Calendar (`/calendar`)

- Month view (default), week view, list view
- Filter by library, media_type, source (wanted vs monitored)
- Click on a date shows all releases that day
- Icons per media type + provider badge
- Personalized: only your wanted + globally-monitored series
- Deep link to "add to wanted" if you spot something on a nearby date

### Lists (`/lists`)

- Configured external lists (Trakt / IMDB / TMDB)
- Add/edit/remove list config
- Sync interval per list
- Last-sync status + result summary ("Added 3, skipped 12 already-wanted, 1 error")
- Manual "sync now" button
- View pending items from a list before they auto-import to wanted

### Monitored series (`/monitored`)

- List of series flagged as monitored
- Next-episode air date + season/episode numbers
- Toggle active/paused
- Add-from-library button (pick a shows library entry to monitor)
- Auto-populates release_calendar on sync (daily)

### Requests bridge (`/requests`)

- Reads requests.ishimura.lol's SQLite DB directly (shared filesystem on ishimura)
- Shows pending + approved requests
- One-click "add to wanted" (auto-TMDB search, populate wanted entry)
- Auto-close request when its wanted item's status flips to `imported`
- Two-way sync: user marks a request as approved in requests.ishimura.lol, Refinery flips its status here

### Extras management (per-item)

On the item detail page (existing) add an Extras section:

- Buttons per extra type: Behind the Scenes / Deleted Scenes / Featurettes / Interviews / Trailers / Shorts / Other
- Each opens a small upload/drag flow that places the file in the Jellyfin-compatible subfolder alongside the main media
- Trailer button also triggers yt-dlp fetch from TMDB's YouTube trailer URL if one exists

### Storage view (`/storage`)

- Per-library disk usage (folder size + item count)
- Format breakdown (codec / resolution / audio) - queried from mediainfo per file
- Duplicate detection results
- Upgrade candidates (files older than release year with lower-quality tags)
- NFS mount capacity + mergerfs branch balance (reads from ishimura's mergerfs)

### Health (`/health`)

Small dashboard pinging adjacent services:

- Jellyfin `/health` + `/Sessions` count
- Navidrome (or successor) `/ping`
- BookLore `/`
- RomM `/api/heartbeat`
- qBittorrent Web UI (behind tailnet)
- slskd `/api/v0/application`
- IGDB / TMDB / OpenLibrary / Trakt API reachability

Similar in spirit to Bridge's Deck grid but scoped just to Refinery's data-flow dependencies.

## Naming template engine

Existing per-type paths are hardcoded. Grow into per-library configurable templates with format specs:

**Movie:**

```
{title} ({year}) [{provider}id-{id}]/
  {title} ({year}) [{provider}id-{id}] - [{source}-{resolution}][{audio_codec} {channels}][{video_codec}]-{group}.{ext}
```

**TV Show:**

```
{title} ({year}) [{provider}id-{id}]/
  Season {season:02d}/
    {title} ({year}) - S{season:02d}E{episode:02d} - {episode_title} [{source}-{resolution}][{audio}][{codec}]-{group}.{ext}
```

Live preview in the template editor UI. Bulk-rename button applies a changed template to every existing item in that library.

## List sync mechanics

**Trakt (public lists, public watchlists):** GET `https://api.trakt.tv/users/<user>/lists/<slug>/items` with `Content-Type: application/json` + `trakt-api-version: 2` + `trakt-api-key: <client_id>`. Just client_id, no OAuth.

**IMDB (public lists):** No official API. Fetch `https://www.imdb.com/list/<listId>/export` as TSV. Or scrape the HTML list page.

**TMDB (public + private):** GET `https://api.themoviedb.org/3/list/<id>` with API key.

Sync loop:

1. Fetch list items
2. Cross-reference against existing `wanted` + `items` (already-owned)
3. New items → insert into `wanted` with status `wanted`
4. Log the diff to `list_syncs.last_sync_result`

Runs on a background scheduler (APScheduler) at each list's configured interval.

## Release calendar mechanics

Nightly refresh:

- For each wanted movie: TMDB movie details → release date if in future
- For each monitored series: TMDB `/tv/<id>/season/<current>` → episode air dates
- Insert into `release_calendar` (upsert on unique key)
- Ntfy push 24h before release date for wanted items only (not every monitored episode - that's spammy)

## Refinery extension phases

### Phase 1 - Library definitions (1 week)

- Libraries table + settings page
- Migrate hardcoded per-type paths to per-library config
- Naming template editor with live preview
- Backfill existing libraries from current folder structure
- No behavior change for existing intake flow

### Phase 2 - Wanted list + requests bridge (1 week)

- Wanted table + Wanted UI
- Add-item flow (TMDB/IGDB/OpenLibrary search)
- Requests bridge (read requests.db, mirror pending items, one-click add)
- Auto-highlight queue items that match wanted
- Auto-close request on import

### Phase 3 - List sync (3-5 days)

- Trakt + IMDB + TMDB list providers
- List config UI
- Background sync scheduler
- Manual sync button

### Phase 4 - Release calendar + monitored series (1 week)

- Monitored series table + UI
- Calendar table + nightly refresh
- Calendar UI (month/week/list views)
- Ntfy push 24h before wanted release dates
- Feed `daily.ishimura.lol`'s Release Calendar section

### Phase 5 - Extras + trailer downloads (3-5 days)

- Per-item extras management UI
- yt-dlp trailer fetch from TMDB
- Jellyfin-compatible subfolder placement
- OpenSubtitles integration for auto-fetch on approve

### Phase 6 - Storage + health (3-5 days)

- Storage view with format breakdown
- Duplicate detection
- Upgrade candidates
- Health dashboard for adjacent services

### Phase 7 - Bulk rename + polish (3-5 days)

- Bulk-rename existing library items to match new templates
- Backup/restore for Refinery DB + settings
- Manual media entry (no provider needed - fan edits, obscure content)

## Data sources

| Signal | Source |
|---|---|
| Movie/TV metadata | TMDB API |
| Anime metadata | AniList (GraphQL) |
| Fan edit metadata | IFDB (fanedit.mcgown.dev) |
| Book metadata | OpenLibrary + Google Books |
| Game metadata | IGDB (already integrated) |
| Music metadata | Bandcamp + Last.fm + Discogs (already integrated) |
| Subtitles | OpenSubtitles API |
| Trailers | TMDB YouTube URLs + yt-dlp |
| Trakt lists | Trakt API (client_id only) |
| IMDB lists | Public list export (TSV) |
| Requests | requests.ishimura.lol SQLite DB (shared FS) |

## Secrets

Add to sops:

- `refinery/tmdb_read_access_token` (already exists as `tmdb/read_access_token`)
- `refinery/opensubtitles_api_key` (new)
- `refinery/trakt_client_id` (new)
- `refinery/igdb_client_id` + `refinery/igdb_client_secret` (already exist as `romm/igdb_*`)

## Ties into

- [[requests]] - Refinery's wanted list is the sink for requests; auto-close on import
- [[daily]] - Release Calendar section pulls from Refinery's `release_calendar` table
- [[stats]] - Refinery approvals feed events into stats
- [[bridge]] - Bridge's health dashboard checks Refinery status; Bridge's storage view overlaps with Refinery's storage tab (Bridge is host-level, Refinery is library-level)
- [[hangar]] - unrelated (game servers)

## Open questions

- **Migration cost** - Refinery's existing intake flow is battle-tested; changing per-type paths to per-library config needs a careful migration to not break existing queue items
- **AniList detection** - Jellyfin library folder + Anilist search is fragile; may need per-item override for edge cases
- **Trakt vs IMDB list precedence** - if a movie is on both lists at different priorities, which wins? Probably highest-priority list wins
- **Monitored series auto-fetch** - do we automatically request downloads via qBittorrent/slskd, or just mark the wanted item and let the manual download flow continue? MVP: manual (Refinery isn't a downloader)
- **Release calendar retention** - keep past events? Prune older than 30 days? Configurable

## Non-goals (revisited)

- Refinery still doesn't download files (slskd + qBittorrent + jdownloader own that)
- Refinery still doesn't stream (Jellyfin/Navidrome own that)
- Not building a request UI (requests.ishimura.lol stays the request entry point)
- Not building a mobile app (web UI is enough)

---

## Current Refinery status (as of 2026-07-08)

Snapshot of what's shipped in the existing Refinery service before this arr-expansion begins.

- **Music:** shipped and polished - MusicBrainz + LRCLib + Deezer + ListenBrainz + Last.fm, spectrograms, ReplayGain, transcode detection, library radar, downloader, bulk fix-missing-art, reprocess script
- **Books:** shipped - OpenLibrary + Calibre, edit page, radar, missing-books
- **Games:** shipped through phase 2 - platform taxonomy, ClrMamePro DAT hash cache, IGDB enrichment, CHD conversion with pre-flight cue validation + 10-min timeout
- **Video:** shipped - guessit + TMDB, movies + shows (season-item + episode-tracks), anime/documentary/short_film subtype auto-classification, Jellyfin folder layout, NFO fallback for TMDB/IMDB ids, sample-file skip, Subs/ folder support, video radar (TMDB next_episode_to_air), missing-episodes detector, bulk-approve TMDB-matched movies, ANSI-stripped log SSE, mergerfs posix_acl-aware writes, `.cue`/`.bin` companion move on approve
- **Subtitles:** OpenSubtitles v1 client wired in `subtitles.py` - dormant, activates when `OPENSUBTITLES_API_KEY` is set
- **Cross-cutting:** tabbed queue by media type, upload/URL-download, source-path-on-approve, nightly DB backup, bulk retry-failed, forget-decision, ACL grants (including video library roots), item id stability via `upsert_item` helper (`INSERT ... ON CONFLICT DO UPDATE` in db.py), error-column clearing on retry-success

## Outstanding refinery-side items (from before arr expansion)

- **Enable OpenSubtitles:** sign up at opensubtitles.com, get API key. Steps: `sops secrets/secrets.yaml` to add `opensubtitles/{api_key,username,password}`; declare in `modules/nixos/ishimura/sops.nix`; swap empty lines in `refinery.nix` env for `${config.sops.placeholder."opensubtitles/api_key"}` etc; deploy. Fetch is per-approve via checkbox on video edit page. Default langs `en` via `REFINERY_SUBTITLE_LANGS`.
- **User side:** subscribe to `ishimura-refinery` topic in ntfy phone app + add topic in ntfy web UI for notification history
- **Real-world video test:** processor built + builds green but hasn't been exercised against a live drop yet

## Fretboard + custom music service integration

When the Navidrome successor ships (see `2026-07-09-services-roadmap.md`), Refinery gains a tab-file media type:

- New library type `tabs` with `/mnt/storage/media/tabs` target
- Scanner extension classifies `.gp`, `.gpx`, `.gp5`, `.xml`, `.mid` files as `game_type = "tab"` and routes through a new `tabs.py` processor
- Metadata extraction via PyGuitarPro (song title, artist, tuning, tempo, difficulty)
- Approve flow imports into fretboard's DB via HTTP POST to fretboard's ingest endpoint
- This unifies music + tabs intake through the same refinery pipeline so uploading a `Master of Puppets - guitar tabs.zip` to slskd gets staged, matched to the album, and dropped into Fretboard's library alongside the album's audio
