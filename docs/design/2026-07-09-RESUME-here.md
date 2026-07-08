# Resume work here - 2026-07-09 spec batch

Context: token budget hit mid-batch. Everything below either needs a full spec file written or an extension applied to an existing spec. Content is complete enough to write from directly - just needs formatting into individual doc files.

## Status

**Written specs (do not re-do):**
- `2026-07-09-bridge-design.md`
- `2026-07-09-refinery-arr-design.md`
- `2026-07-09-stats-extension-design.md`
- `2026-07-09-vtt-design.md`
- `2026-07-09-games-hub-design.md`
- `2026-07-09-fretboard-design.md`
- `2026-07-09-services-roadmap.md`
- `2026-07-09-dotfiles-cleanup-todo.md`
- `2026-07-09-booklore-replacement-design.md`
- `2026-07-09-music-service-design.md`
- `2026-07-09-romm-replacement-design.md`

**Still to write (as own spec files):**
- `2026-07-09-jellyfin-frontend-design.md`
- `2026-07-09-synctube-replacement-design.md`
- `2026-07-09-wiki-design.md`
- `2026-07-09-page-archiver-design.md`
- `2026-07-09-recipe-manager-design.md`
- `2026-07-09-intercom-design.md`
- `2026-07-09-small-utilities-design.md`

**Extensions to existing specs still pending:**
- `2026-07-09-bridge-design.md` gains: Scrutiny replacement, cert/domain/license/subscription expiry board, DNS stats dashboard, data-flow cockpit, nix-topology diagram, ship's log
- `2026-07-09-stats-extension-design.md` gains: crew roster with positions (Engineer/Security/Medical/Science/Miner/Recreation Officer) driving badges + UI + minor perms + `Sec/Username` aliases; watchlist + reviews + ratings feature (finished-and-rated feeds taste profile)
- `2026-07-08-daily-design.md` gains: Ishimura Bugle (auto-generated monthly newsletter aggregating top-watched media, most-active crew, new mods, recovered logs; cross-post to intercom + email)

## Original Prompt

A few more things, and this one is a word dump, basically different sentences from earlier
brainstorming. 

"Okay a few more specs and changes to existing ones.

- Scrutiny replacement (preferably as a part of bridge)
- Moodist diy replacement
- Booklore replacement with feature parity with booklore and and kobo sync support.
- SyncTube Replacement
- Navidrome replacement that is fully subsonic compatible so I can keep using apps. with radio /
  podcasts (maybe fretboard integrated instead of seperate)
- Romm replacement
- Maybe since jellyfin replacement is unrealistic, maybe just a frontend for jellyfin that we can theme
  fully that uses jellyfin behind the scenes? This way we can still connect to jellyfin on apps.
- Privatebin replacement
- Wiki for guides on ishimura and also maybe a wiki for archives of sites like wikipedia
- Some kind of system for watchlists/reviews/ratings not sure if this should be seperate or included in
  something like profile/stats/requests
- Guest book
- Certs / domain / license / subscription expiery board (probably built into bridge)
- DNS stats dashboard - Complement to AdGuard: most-blocked, per-device breakdown, top talkers (part of
  bridge)
- Movie/game night scheduler
- Private URL shortener
- page archiver + bookmark manager with per user bookmarks
- Recipe manager
- Maybe something like this in bridge? "Data-flow cockpit - One view of the whole media pipeline: slskd
  complete → refinery queue → Jellyfin/Navidrome/RomM/BookLore. What's stuck where."
- And maybe something like https://github.com/oddlama/nix-topology for bridge.
- Ship's log / captain's diary - Themed daily-journal specifically for ishimura roleplay.
  Auto-generated entries from system events ("2026-07-08 - Refinery processed 12 items. KF2 uptime 4
  days."). Fits the Dead Space vibe. in bridge
- Crew roster - Users pick a "position" at signup (Engineer, Security, Medical, Science, Miner,
  Recreation Officer). Position dictates their badge, some UI hints, maybe minor permissions or
  exclusive views. Aliases show as Sec/MaxwellPayne. ~3-4 evenings.
- Ship intercom - Themed shared bulletin/chat. CEC letterhead formatting, timestamps in fake
  shipboard dating, static/interference effects on old messages. Async, but the intercom "chirps" when
  someone posts. Forum/bbs board style
- Anonymous suggestion box - Physical-looking terminal on the site where users drop ideas/complaints
  anonymously into a CEC-branded "employee feedback" queue. Admin reviews later. 
- contact me form
- Ishimura Bugle - Auto-generated monthly newsletter. Top-watched media, most-active crew, new mods
  installed on game servers, latest recovered logs. Emailed or dropped in the intercom. (a part of daily I guess)"


## User decisions from this session

- **Fretboard fate:** keep the fretboard spec as a phase-1 reference; folds into music-service later. Cross-referenced in music-service spec. Noted as open question in music-service. Decide when we get there.
- **Jellyfin frontend:** bypass Jellyfin login via voidauth OIDC directly against the themed frontend (long-run cleaner). Native mobile/TV apps keep hitting Jellyfin's own auth as usual.
- **Movie/game night scheduler:** NOT a standalone. Absorbed into intercom (session coordinator: SyncTube + Jellyfin syncplay + ROMM netplay + rec room coop + hangar servers via API calls).
- **Guest BookLore:** just a guest-share-token feature inside booklore-replacement. Already covered.
- **Intercom real-time vs async:** undecided. Put as open question in the spec.
- **Doc style:** short and sweet but complete. Every feature covered, no bloat.

## Spec skeletons to expand into individual files

### 2026-07-09-jellyfin-frontend-design.md

**One-liner:** Fully-themed browser frontend that reverse-proxies Jellyfin's HTTP API. Voidauth OIDC replaces Jellyfin login for the web experience. Native Jellyfin apps (mobile, TV, Roku) continue hitting Jellyfin's own auth transparently.

**Why:** Jellyfin's web UI can't be fully themed (post-login CSS overrides break on version bumps). Building a frontend gives us total design control without losing Jellyfin's transcoding, mobile apps, and Chromecast.

**Architecture:**
- Flask on ishimura, port `5016`, nix module `modules/nixos/ishimura/jf-frontend.nix`
- Voidauth-forwardauth on all `/jf/*` routes (browser use); Jellyfin subdomain stays unauthed for native apps
- On voidauth login, exchange OIDC token for a Jellyfin API key by calling Jellyfin's `/Users/AuthenticateByName` server-side (or use a pre-provisioned service account per user - decide during impl)
- Proxy Jellyfin API responses through, rewrite URLs to relative paths, inject themed HTML shell around the video player

**Features:**
- Full themed browse UI: libraries, movies, shows, music (yes, we serve music separately but Jellyfin still owns some), collections, playlists
- Themed HTML5 video player wrapping Jellyfin's playback endpoints (HLS + DASH + direct play)
- Live TV + DVR pass-through if Jellyfin is configured for it
- Search across libraries
- SyncPlay support (Jellyfin's own feature, exposed through themed UI)
- Watch progress synced to Jellyfin
- Subtitle track selection
- Chapter navigation
- Server-side rendered library grid (no JS-only SPA - faster)
- Native app deep-link: "Open in Jellyfin app" button on every media detail page

**Ties into:** stats-extension (Now Playing), intercom (session coordinator uses SyncPlay), daily (Now Streaming Aboard), refinery (library refresh triggers)

**Open questions:**
- Per-user Jellyfin auth: pre-provisioned service account per user vs on-the-fly authenticateByName? Impacts admin surface
- Do we need to proxy WebSocket endpoints for real-time playback sync? Probably yes for SyncPlay

### 2026-07-09-synctube-replacement-design.md

**One-liner:** Watch-together with playlist, chat, and room permissions. Sources: YouTube, Vimeo, direct MP4/WebM URLs, Jellyfin library items, HLS streams, Twitch VODs.

**Why:** SyncTube is fine but not themable. Same DIY pattern.

**Architecture:**
- Flask + SocketIO on ishimura, port `5017`, nix module `modules/nixos/ishimura/synctube.nix`
- Persistence `/persist/synctube/synctube.db`
- Voidauth-forwardauth; guest join tokens optional
- Room-per-URL with WebSocket namespace for state sync
- yt-dlp integration for YouTube URL resolution

**Data model:**
```sql
CREATE TABLE rooms (id, slug, name, created_by, created_at, current_media_url, current_position_secs, is_playing, updated_at);
CREATE TABLE room_playlist (id, room_id, media_url, title, added_by, position, added_at);
CREATE TABLE room_members (room_id, username, joined_at, role);  -- role: host / member / guest
CREATE TABLE chat_messages (id, room_id, username, body, sent_at);
CREATE TABLE guest_tokens (token, room_id, expires_at, uses INTEGER, max_uses);
```

**Features:**
- Rooms with slug URL, per-room chat
- Add to playlist: YouTube URL (yt-dlp resolves stream), direct video URL, Jellyfin library item picker (deep-integrate with jellyfin-frontend), Twitch VOD, HLS stream
- Sync via WebSocket: play/pause/seek events broadcast to all members within 500ms
- Host role can override; members can only request scrub
- Guest tokens - non-voidauth users can join via share link
- Chat with emoji, mentions
- Presence indicator (member count, who's watching)
- Voice via Discord (link out; no WebRTC in-app)

**Stages:** MVP room/chat/sync (1 week) → YouTube/Twitch URL support (3-5 days) → Jellyfin library picker (3 days) → guest tokens + permissions (3 days)

**Ties into:** intercom (session coordinator creates synctube rooms), jellyfin-frontend (library picker), comms officer (Discord voice link + room-created notifications)

**Open questions:** WebRTC voice inside the app vs delegating to Discord - Discord for now, revisit if we ever have friends without Discord accounts

### 2026-07-09-wiki-design.md

**One-liner:** Two-in-one: internal guides for the ishimura ecosystem (how to use each service, disaster recovery, ARG hints) + offline archives of external references (Wikipedia, StackOverflow, MDN, Gutenberg) via Kiwix.

**Architecture:**
- Two Flask apps or one with two blueprints
- Internal wiki at `wiki.ishimura.lol`: markdown files in `/persist/wiki/pages/`, git-backed, edit via web (admin group) + git commit auto-picks up new pages
- Archive at `wiki.ishimura.lol/archive/`: Kiwix-serve fronting ZIM files at `/mnt/storage/archives/kiwix/*.zim`
- Voidauth-forwardauth; internal wiki public, archive tailnet-only (legal-safe for personal use)

**Internal wiki features:**
- Markdown pages with wiki-links (`[[page-name]]`)
- Auto-generated index by category
- Full-text search (Whoosh or SQLite FTS)
- Edit via textarea for admins; commits back to `/persist/wiki/pages/` git repo
- ARG-adjacent: some pages have hidden sections unlocked by ARG progression (see intercom + stats-extension)
- Themed with ship aesthetic (monospace, CRT, section dividers)

**Kiwix archive features:**
- Kiwix-serve fronts ZIM files
- Available bundles (decide during install): full English Wikipedia (~100GB), text-only Wikipedia (~10GB), Wikivoyage, MDN Web Docs, StackOverflow-en, Gutenberg English, Wiktionary
- Search across all mounted ZIMs
- Themed CSS overlay via Kiwix's `--customIndex` option

**Stages:** internal wiki MVP (3-5 days) → search + git integration (3 days) → Kiwix archive mount + selected ZIMs (2-3 days) → ARG hidden sections wiring (2 days)

**Ties into:** stats-extension (ARG progression unlocks pages), intercom (public wiki edit event notifications)

### 2026-07-09-page-archiver-design.md

**One-liner:** Per-user bookmarks + Wayback-Machine-style archive of the full page HTML at time of save. Tag search, full-text search, reader-mode extract, screenshot preview.

**Why:** Combines Karakeep + Linkding + ArchiveBox concepts into one Ishimura-shaped tool.

**Architecture:**
- Flask on ishimura, port `5018`, nix module `modules/nixos/ishimura/archiver.nix`
- Persistence `/persist/archiver/archiver.db` + HTML/screenshots at `/mnt/storage/media/archives/{username}/{yyyy-mm}/{hash}.{html,png,pdf}`
- Playwright bundled via nix for headless capture
- Voidauth-forwardauth per-user

**Data model:**
```sql
CREATE TABLE bookmarks (
    id, username, url, title, description, favicon_url,
    tags,               -- JSON array
    reader_extract,     -- Mercury/Readability text extract
    archived_html_path, archived_screenshot_path, archived_pdf_path,
    read_status,        -- unread/read/starred/archived
    added_at, last_read_at
);
CREATE VIRTUAL TABLE bookmarks_fts USING fts5(title, description, reader_extract, tags, content='bookmarks');
```

**Features:**
- Bookmarklet + browser extension (Firefox/Chrome) to save current page
- On save: fetch URL, extract Reader Mode text, screenshot via Playwright, save full HTML, save PDF
- Retry-on-failure job for pages that couldn't be archived first pass
- Tag-based organization, per-user tag suggestions
- Full-text search across reader extracts + titles + descriptions
- Reading list mode (unread/read/starred)
- Themed grid + list views with favicon + preview thumbnail
- Import from Pocket, Instapaper, Raindrop, browser bookmarks
- Public share link per bookmark (guest access to archived version)

**Stages:** MVP bookmarks + Playwright archive (1 week) → tag search + FTS (3 days) → bookmarklet + extension (3-5 days) → import from external services (2-3 days)

**Ties into:** stats-extension (reading events feed activity), daily (bookmark of the day in Op-Ed), intercom (share bookmark to intercom bulletin)

### 2026-07-09-recipe-manager-design.md

**One-liner:** Personal cookbook with tag search, ingredient/pantry tracking, meal planning calendar, and grocery list export. Tandoor DNA in an Ishimura shape.

**Architecture:**
- Flask on ishimura, port `5019`, nix module `modules/nixos/ishimura/recipes.nix`
- Persistence `/persist/recipes/recipes.db` + images at `/mnt/storage/media/recipes/`
- Voidauth-forwardauth

**Data model:**
```sql
CREATE TABLE recipes (id, title, description, source_url, servings, prep_mins, cook_mins, cuisine, tags, image_local, added_by, added_at);
CREATE TABLE ingredients (id, recipe_id, name, quantity, unit, position);
CREATE TABLE steps (id, recipe_id, position, body);
CREATE TABLE meal_plan (id, username, date, meal_type, recipe_id);  -- meal_type: breakfast/lunch/dinner/snack
CREATE TABLE pantry (username, ingredient_name, quantity, unit, expiry_date, PRIMARY KEY(username, ingredient_name));
CREATE TABLE cooked_history (id, username, recipe_id, cooked_at, notes, rating);
```

**Features:**
- Recipe entry: manual + URL import (scrape common recipe sites via structured data, JSON-LD `Recipe` schema)
- Ingredient with quantity/unit; auto-scale on servings change
- Meal plan calendar per user
- Grocery list: compute delta between meal plan and pantry, export as printable + shareable list
- Pantry tracker with expiry alerts (ntfy push 2 days out)
- Cooked-history + user rating feeds "what should I cook tonight?" suggestions
- Photo upload per recipe
- Tag search + full-text search
- Themed print mode for physical recipe cards

**Stages:** MVP recipes + ingredients + steps (3-5 days) → meal plan calendar (3 days) → grocery list + pantry (3 days) → URL import + photo upload (2-3 days)

**Ties into:** stats-extension (cooked events + ratings feed activity), daily (recipe of the week in classifieds), intercom (share recipe to bulletin)

### 2026-07-09-intercom-design.md

**One-liner:** Themed shared bulletin/BBS forum with session coordinator for spinning up cross-service co-play (SyncTube + Jellyfin syncplay + ROMM netplay + rec deck coop + hangar servers). CEC letterhead formatting, chirp notifications on new posts.

**Architecture:**
- Flask + SocketIO on ishimura, port `5020`, nix module `modules/nixos/ishimura/intercom.nix`
- Persistence `/persist/intercom/intercom.db`
- Voidauth-forwardauth; posts attributed to crew profile (stats-extension); rank + position badges rendered inline

**Data model:**
```sql
CREATE TABLE boards (id, slug, name, description, position, admin_only BOOLEAN);
CREATE TABLE threads (id, board_id, author, title, body_markdown, pinned, locked, view_count, created_at, updated_at);
CREATE TABLE posts (id, thread_id, author, body_markdown, edited_at, created_at);
CREATE TABLE reactions (post_id, username, emoji, PRIMARY KEY(post_id, username, emoji));
CREATE TABLE subscriptions (username, thread_id, notify_on TEXT, PRIMARY KEY(username, thread_id));  -- notify_on: all / mention / none
CREATE TABLE bulletins (id, author, body, expires_at, pinned, created_at);  -- short-form announcements
CREATE TABLE sessions (id, kind, coordinator, media_ref, external_ids, state, created_at);
  -- kind: syncplay / synctube / rom-netplay / rec-coop / hangar-invite
  -- external_ids: JSON with room IDs / party IDs / server IDs to reach the target service
```

**Features:**

**Forum/BBS side:**
- Boards: General, Media, Games, ARG, Announcements (admin-only)
- Threads + posts with markdown, emoji reactions, mentions, per-thread subscriptions
- CEC letterhead: forms styled as CEC memos, timestamps in fake shipboard dating alongside real UTC
- Static/interference effects on posts older than 30 days (visual only)
- "Chirp" notification: subtle audio + ntfy push when a subscribed thread gets a new post
- Rank + position badges (from stats-extension) render inline next to author name
- Short-form bulletins at the top of the front page (like a shared announcement board)
- Anonymous suggestion box board (posts show "ANONYMOUS CREWMEMBER" instead of username)
- Search across posts + threads

**Session coordinator:**
- Create a session from a thread with `[SESSION]` button
- Kind picker: SyncTube movie, Jellyfin SyncPlay, ROMM netplay, Rec Deck coop game, Hangar server invite
- Coordinator calls each target service's API to create/join a room, collects the join URLs
- Session card in the thread shows: current members (real-time via WebSocket), join buttons, "currently playing" for each service
- Auto-post to Discord (via Comms Officer) with join links
- Poll option: create a poll to schedule vote (e.g. "Movie night this Friday", 4 options), winning option auto-creates session at scheduled time
- ntfy push 15 min before scheduled session

**Stages:** MVP boards/threads/posts/reactions (1 week) → subscriptions + chirp + search (3-5 days) → session coordinator MVP with SyncTube + Hangar (1 week) → Jellyfin syncplay + ROMM netplay + rec deck (1 week) → polls + scheduling (3-5 days)

**Ties into:** stats-extension (author rank/position badges + activity events), comms officer (cross-post sessions + polls to Discord), synctube/jellyfin-frontend/roms/rec-deck/hangar (session coordinator API consumers), daily (top-of-week thread in Op-Ed)

**Open questions:**
- **Real-time vs async:** post arrival is async (chirp is a notification, not a live-thread stream). Could add live "N crew are viewing this thread" indicator via WebSocket. Decide during impl.
- Rate limiting: post spam prevention - N posts/hour per user?
- Threading depth: flat replies (like Discord) or nested (like Reddit)?

### 2026-07-09-small-utilities-design.md

**One-liner:** Grab-bag of small Ishimura-themed utilities each too small to warrant its own spec. Each section documents one utility.

**Section 1: Moodist DIY**
- Static site with 12-18 curated ambient sound files (rain, wind, engine hum, ship creaks, hydroponics, ambient CEC intercom, marker signal, low reactor hum)
- Per-sound volume mixer + master
- Save presets (up to 6 per user)
- Web Audio API mixing
- URL: `moodist.ishimura.lol`; nix module `modules/nixos/ishimura/moodist.nix`; ~2 evenings

**Section 2: PrivateBin replacement**
- Client-side encrypted pastebin
- AES-256-GCM in the browser, server sees only ciphertext + IV + salt
- Expiry (5min / 1hr / 1day / 1week / burn-after-read)
- Attachment support (encrypt + upload)
- Themed with CRT + terminal aesthetic
- URL: `paste.ishimura.lol`; port `5021`; ~1 week

**Section 3: Private URL shortener**
- Voidauth-gated shortener at `s.ishimura.lol/<slug>`
- User-picked or auto-generated slug
- Public redirects (no auth on the redirect endpoint)
- Analytics: click count, first-seen, per-slug rolling 30d graph
- Vanity slugs reserved for admin
- URL: `s.ishimura.lol`; port `5022`; ~2-3 days

**Section 4: Anonymous suggestion box**
- Small Flask endpoint that accepts suggestions with no auth on the submit form
- CEC-branded "employee feedback tube" aesthetic
- Admin queue at `/admin/suggestions` with mark-read/dismiss/respond
- Optional email response if submitter provided contact
- Actually just a route on the intercom service (see intercom's Anonymous suggestion box board). This section here is if we ever want a standalone version.
- URL: could be `feedback.ishimura.lol` or absorbed into intercom; ~2 evenings

**Section 5: Contact me form**
- Public form at `ishimura.lol/contact`
- Fields: name, contact (email/handle), subject, message
- Sends via Resend SMTP to admin
- Anti-spam: honeypot + Anubis PoW challenge
- Confirmation message + optional auto-reply
- Small addition to homepage overlay, not its own service; ~1 evening

## Bridge extensions to apply

Add to `2026-07-09-bridge-design.md`:

### Scrutiny replacement

Disk SMART monitoring panel. Reads `smartctl` output on each host, stores per-device history, renders health overview.

- Background collector on each host reads `smartctl -a -j <device>` for each SATA/NVMe/USB drive
- Push to Bridge every hour + on-demand from UI
- Table schema: `disk_health_history(host, device, model, serial, temp_c, hours_on, reallocated_sectors, pending_sectors, uncorrectable_sectors, wear_leveling_pct, health_json, recorded_at)`
- Alert rules: reallocated > 10 → yellow, pending > 0 → yellow, uncorrectable > 0 → red, temp > 55°C sustained → yellow, wear > 90% → red
- Grafana-style trend graphs per device on Bridge's Infrastructure Deck
- Ntfy push on new red

### Certs + domain + license + subscription expiry board

Countdown board of everything that expires.

- Manual entries + auto-detected (SSL certs from Traefik state, domain from Porkbun API, VPS/Servury subscription date)
- Table: `expiry_items(id, kind, name, expires_at, source, notes)`; kind: cert / domain / license / subscription
- Sortable by soonest expiry
- Ntfy push 30 days out + 7 days out + 1 day out
- Auto-refresh cert expiries from Traefik/certbot state file
- Auto-refresh domain expiries via Porkbun API (sops key)

### DNS stats dashboard

AdGuard Home stats surfaced with better viz.

- Poll AdGuard Home API every 5 min for query log stats
- Table: `dns_stats_history(hour, host, total_queries, blocked_queries, top_domains, top_clients)`
- Bridge UI: most-blocked domains (day/week/month), per-device breakdown (top talkers), query volume timeline, block rate
- Filter by device (client name from AdGuard)
- Click-to-drilldown per domain (show which client requested it, when, how many times)

### Data-flow cockpit

One view of the entire media pipeline.

- Reads: slskd `/api/v0/searches` + `/api/v0/downloads`, Refinery `/queue`, Jellyfin `/Users/{id}/Items/Latest`, music service `/api/scan-status`, ROMs service `/api/recent`, BookLore service `/api/recent`
- Renders as a horizontal Sankey/waterfall: `slskd → refinery inbox → refinery queue → refinery approved → jellyfin/music/roms/booklore → played by user`
- Highlight stuck items: in slskd complete but not in refinery inbox after 1h, in refinery queue > 24h, approved but not seen by downstream service
- Manual re-trigger buttons per stage (call refinery scan, call jellyfin library refresh)

### nix-topology diagram

Auto-generated architecture diagram.

- Use `oddlama/nix-topology` flake to generate SVG of the topology
- Renders hosts + services + tailnet links + sops secret usage as a graph
- Bridge serves the generated SVG at `/topology`
- Rebuilt on nix flake update via systemd service
- Interactive: click a service to jump to its Bridge card

### Ship's log / captain's diary

Auto-generated Dead Space themed daily journal.

- Every day at 09:00 UTC, generate a diary entry from the last 24h of Bridge's Captain's Log + host stats + service events
- Template:
  ```
  SHIP'S LOG :: 6.34.847 :: MAINTENANCE OFFICER PAYNE

  Reactor output steady at 47%. All decks nominal.

  REFINERY processed 12 items overnight. HANGAR reports 4 days uptime on VS.
  KF2 saw active session with 3 crew. TARKOV-SPT quiet.

  Notable events:
   - Systems technician Denise unlocked "Night Owl" - 25 pts
   - Bridge officer MaxwellPayne resolved ALERT-47 (Refinery disk warning)
   - New content: 8 media items approved

  Reactor forecast: nominal. Next scheduled maintenance: 6.35.847.
  ```
- Rendered on Bridge homepage above card grid
- Archived under `/log/YYYY-MM-DD`
- Cross-post to intercom's General board + Discord via Comms Officer
- Optional: LLM (local Ollama) can rewrite the daily template into more atmospheric prose if we want

## Stats-extension extensions to apply

Add to `2026-07-09-stats-extension-design.md`:

### Crew roster with positions

Users pick a "position" at first login (or admin assigns): Engineer, Security, Medical, Science, Miner, Recreation Officer.

- Position stored on `crew_users` table (add `position` column)
- Each position has: badge icon, accent color, minor UI hints, some position-exclusive views
  - Engineer: sees hardware/infrastructure widgets emphasized, exclusive access to a "wrench" theme accent
  - Security: sees Captain's Log excerpts on their profile, alerts subscription default on
  - Medical: sees stats/wellness widgets emphasized ("crew health monitor" persona)
  - Science: sees research-flavored widgets (species catalog, discovery log tied to ARG)
  - Miner: sees resource/production metrics prominently (refinery output, storage usage)
  - Recreation Officer: sees Rec Deck stats first, moderator perms on intercom rec-related threads
- Aliases render as `Sec/MaxwellPayne`, `Med/Denise`, `Eng/OccultaDomina` across UI
- Position is cosmetic + soft-permissions (Recreation gets rec-deck moderator; Security gets alert-ack-without-details); admin still has full override

### Watchlist + reviews + ratings

Adds finished-and-rated state as a new activity signal.

- New table:
  ```sql
  CREATE TABLE user_reviews (
      id INTEGER PRIMARY KEY,
      username TEXT NOT NULL,
      media_type TEXT NOT NULL,      -- movie, show, anime, song, album, book, game
      external_id TEXT,              -- tmdb:X / mbid:X / igdb:X / isbn:X
      title TEXT NOT NULL,
      rating INTEGER,                -- 1-10
      review_text TEXT,
      finished_at TIMESTAMP,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(username, media_type, external_id)
  );
  ```
- Watchlist ("want to consume") is already covered by requests' wanted list - don't duplicate
- Currently-consuming is already covered by Now Playing widget
- Finished-and-rated is the new bit
- API: `POST /api/review`, `GET /api/reviews/<user>`, `GET /api/review-avg/<external_id>` (crew average)
- Review submissions boost that media's genre weights in the reviewer's taste profile (stronger positive signal than a passive play)
- Renders on profile page: "Recent reviews" block
- Feeds Requests' Discover tab: "similar to what you rated highly"
- Reviews visible on media detail pages (jellyfin-frontend, music-service, romm, booklore) as small avatar-attributed cards
- Crew average rating shown next to media in library browsers

## Daily extensions to apply

Add to `2026-07-08-daily-design.md`:

### Ishimura Bugle (auto-generated monthly newsletter)

New section on the last day of each month.

- Auto-generated aggregated content:
  - Top 5 most-watched movies + shows (from stats)
  - Top 5 most-played songs (from stats)
  - Most-active crew (top 3 by activity score)
  - Rank promotions this month (crew who leveled up)
  - New games/mods installed on Hangar servers
  - Latest recovered logs (from ARG)
  - New media additions (top 10 by user interest)
  - Notable Captain's Log entries (system incidents, big alerts resolved)
- Publishes to `/bugle/YYYY-MM` archive
- Front page front-and-center on publish day
- Cross-post to intercom's Announcements board
- Email to opted-in subscribers via Resend
- Ntfy push on publish
- Themed layout: CEC quarterly newsletter aesthetic, single-page scroll, ASCII banner header

## After this batch is done

Delete this RESUME file. Nothing else in memory folder is orphaned.

Confirm all deleted memory files stayed absorbed: `notes/memory/` should be empty. Confirm all new specs exist:

```
ls notes/specs/2026-07-09-*.md
```

Expected count: 19 files (11 already-written + 7 new from this batch, plus this RESUME which gets deleted).

## Priority order for the resume

If tokens are tight, prioritize in this order:

1. **Intercom + small-utilities** (biggest bang for buck; unlocks a lot of ecosystem cross-linking)
2. **Bridge extensions** (Scrutiny + expiry board + DNS + data-flow + nix-topology + ship's log) - Bridge gains a lot of real utility
3. **Music service** - already done
4. **Recipe manager + page archiver + wiki** (personal-use daily-drivers)
5. **Jellyfin frontend** (nice to have, but Jellyfin's existing UI works)
6. **SyncTube replacement** (nice to have, SyncTube works today)
7. **Stats-extension + daily extensions** (small edits, quick)

If very tight, ship intercom + all extensions and call it done. The individual replacement specs (music, roms, booklore) are already in the "later" pile since those services aren't blocking anything.
