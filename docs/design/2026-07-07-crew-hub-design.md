# Crew Hub Design (`ishimura.lol/crew`)

**Status:** design approved 2026-07-07, ready for implementation planning.

## Goal

Unified per-user profile page + admin dashboard + user-to-user messaging on the ishimura homelab, hosted on the homepage domain (not a separate subdomain) so it feels like a native part of the site.

Existing services keep their own domain and their own concerns; the crew hub is the meta-layer that ties them together for a "here's everything about this crew member" view.

## Non-goals

- Not a new subdomain (would feel like a separate service)
- Not folded into stats (stats stays focused on activity aggregation)
- Not folded into rec deck (couples "profile" to "games" service)
- Not real-time chat (Discord handles group; DMs are async notes)
- Not group chats or channels (Discord's job)
- Not friend requests (small friend group, everyone can DM everyone)
- Not real-time messaging in MVP (polling is fine)
- Not push notifications in MVP (in-app badge only)

## Architecture

### Hosting

Two new small Flask apps on normandy (same host as the static homepage):

- `ishimura-crew` at `127.0.0.1:8087` - handles `/crew/*` on `ishimura.lol`
- `ishimura-admin` at `127.0.0.1:8088` - handles `/admin/*` on `ishimura.lol`

The existing static busybox homepage stays at the root, serving `ishimura.lol/`. Traefik on normandy routes:

- `Host(ishimura.lol) && PathPrefix(/crew)` → `ishimura-crew`
- `Host(ishimura.lol) && PathPrefix(/admin)` → `ishimura-admin`
- `Host(ishimura.lol)` (priority 5) → existing static homepage (unchanged)

Both new apps sit behind `voidauth-forwardauth` middleware so `Remote-User` and `Remote-Groups` headers are available.

The existing `/admin` router's `tailnet-only` middleware is **removed**. Admin access is now voidauth-role-gated instead of IP-gated.

### Why two Flask apps, not one

- Different auth policies: crew allows any authenticated voidauth user; admin only allows users in the `admin` group. Clean at the app boundary (`before_request` handler)
- Different blast radius: a bug in the frequently-changing crew app can't compromise admin
- Different change velocity: crew iterates a lot; admin is stable
- Matches existing per-concern Flask pattern (requests, refinery, games, stats each get their own small app)

Shared code (voidauth identity parsing, avatar helper, group check) lives in a small `config/ishimura_shared/` module both apps import.

## Crew profile page (`/crew/<user>`)

Single-scroll layout with sections that swap self-view vs other-view.

### Sections

**Header**
- Avatar (dicebear ~120px), username, member-since date
- Badges: admin group indicator + custom title (from future cosmetics shop)
- Optional: online-now dot based on `last_active_at` from crew_users table

**Stats grid**
- ~12 stat cards covering both games and media
- Games (from `games:5001/api/user/<user>/dossier`): Chess Elo, Chess Wins, Chess Games, Tickets, Tickets Lifetime Won, Arbiter Wins, Blackjack Hands, Slot Spins
- Media (from new `stats:5005/api/user/<user>/summary`): Watch Time, Songs Played, ROMs Played, Books Read, Reading Time, Rec Deck Plays
- Same visual style as existing stats overview cards

**Recent activity feed** (last ~20 events)
- From new `stats:5005/api/user/<user>/recent?limit=20`
- Cross-source events: `3h ago :: watched Alien on Jellyfin`, `5h ago :: won a chess game vs kendra`, etc.
- Public events only (games completions, media playback); no private DMs

**Messages**
- Self-view: inbox of received messages + list of conversations
- Other-view: single "SEND MESSAGE" button that opens compose to this user

**Settings & links** (self-view only)
- Link to voidauth for account/password
- Link to `avatars.ishimura.lol` for avatar customization
- Notification preferences (future)
- Achievement grid (future)

**Crew roster link** (top of page)
- Small `// CREW ROSTER (7)` link linking to `/crew/` index page
- Roster page shows list of all voidauth users with avatars for browsing

### Access rules

- Any voidauth-authed user can view any `/crew/<other_user>`
- Self-view (`/crew/<self>` or `/crew/me`) additionally shows messaging inbox + settings
- Admin console link only appears if viewer's `Remote-Groups` includes `admin`

## Nav widget

Shared JS widget served from `https://ishimura.lol/crew/nav-widget.js`, embedded in each ishimura service via a script tag and two meta tags.

(URL prefix is `/crew/` because the static homepage owns the root at `ishimura.lol/*`. Serving `/nav-widget.js` from the root would either need a dedicated Traefik rule to route just that path to the crew Flask app, or the file to be copied into the static homepage. Using `/crew/nav-widget.js` keeps the routing clean - the widget is a crew-app static asset.)

**Each service's `base.html` adds:**

```html
<meta name="ishimura-user" content="{{ user }}">
<meta name="ishimura-groups" content="{{ groups|default('') }}">
<script src="https://ishimura.lol/crew/nav-widget.js" defer></script>
```

**Note for each service's Flask app:**

Each service needs to add `groups` to its render context, reading from `Remote-Groups` header. Small helper in `config/ishimura_shared/voidauth.py` will handle this so each service just calls `render_template(..., **voidauth.context())`.

Identity is server-side rendered from `Remote-User` / `Remote-Groups`. No cross-origin API call needed for identity resolution.

**What the widget renders:**

Fixed-position avatar+username button in the top-right corner. Click opens dropdown:

- VIEW MY PROFILE → `/crew/<user>`
- MESSAGES → `/crew/messages` (with unread badge if same-origin)
- ACCOUNT SETTINGS → voidauth account
- CUSTOMIZE AVATAR → `avatars.ishimura.lol`
- ADMIN CONSOLE → `/admin` (only if admin group present)
- LOG OUT → voidauth logout URL

Styled with Shadow DOM to isolate widget CSS from host service styles.

**Unread badge:**

Widget polls `/crew/api/unread-count` every 30 seconds. Because the endpoint is on `ishimura.lol` root and other subdomains would need CORS, MVP shows the badge **only on same-origin (`ishimura.lol` itself)**. Subdomains (rec, stats, etc.) get the dropdown but no live badge. Adding CORS + cookie-sharing so the badge works on all `*.ishimura.lol` subdomains is a Phase 4 enhancement.

**Third-party services:**

Jellyfin, Navidrome, ROMM, Booklore keep their own account menus. Widget doesn't inject there (SPA/CSP fragility). Deferred future option: Traefik body-rewrite injection (same technique as anubis-theme.css).

**Services that adopt the widget in Phase 1:**

Rec deck, requests, refinery, stats, crew (built-in), admin (built-in), avatars page, static homepage. Two lines per service in `base.html`.

## Data flow

Fan-out HTTP fetches on each `/crew/<user>` page load, parallelized in a `ThreadPoolExecutor(max_workers=3)`.

**On page load:**

1. `GET games:5001/api/user/<user>/dossier` (already exists)
2. `GET stats:5005/api/user/<user>/summary` (**new**)
3. `GET stats:5005/api/user/<user>/recent?limit=20` (**new**)

Plus crew app's own DB query for messages inbox (self-view only).

All localhost. Total page load target: ~100ms.

**New endpoints on stats:**

```python
@app.route("/api/user/<username>/summary")
def api_user_summary(username):
    # localhost-only (127.0.0.1/::1 check bypasses Remote-User)
    with db.get_db() as conn:
        return jsonify(db.get_dashboard_stats(conn, username))

@app.route("/api/user/<username>/recent")
def api_user_recent(username):
    limit = int(request.args.get("limit", 20))
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT source, item_type, item_name, played_at FROM events "
            "WHERE user_id=? ORDER BY played_at DESC LIMIT ?", (username, limit)
        ).fetchall()
        return jsonify([dict(r) for r in rows])
```

Same auth exemption pattern used by `games/api/user/*/dossier` (localhost-only).

**Graceful degradation:**

Each fetch: 2-second timeout, wrapped in try/except. Failure returns None; corresponding page section renders `// UNAVAILABLE`. Full page still loads.

**Member-since resolution:**

Fetched from `games` dossier's `created_at`. Fallback to crew_users' `first_seen_at` if user has no games record. Consistent with rec deck's existing display.

**Avatar resolution:**

- MVP: dicebear direct with username (`avatars.ishimura.lol/api/<style>/<username>.svg`)
- Deferred: voidauth OIDC `userinfo` for user-set `picture` claim

**No caching in MVP.** Cross-service data is always fetched fresh. If fan-out becomes slow later, add 30s TTL LRU cache keyed by `(endpoint, username)`.

## Messaging

1-to-1 DMs. No group chats, no reactions/replies in MVP.

### Schema

Crew app's own SQLite at `/persist/crew/crew.db`:

```sql
CREATE TABLE crew_users (
    username        TEXT PRIMARY KEY,
    first_seen_at   TEXT NOT NULL DEFAULT (datetime('now')),
    last_active_at  TEXT NOT NULL DEFAULT (datetime('now')),
    avatar_url      TEXT,
    custom_title    TEXT
);

CREATE TABLE messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    sender    TEXT NOT NULL,
    recipient TEXT NOT NULL,
    body      TEXT NOT NULL,
    sent_at   TEXT NOT NULL DEFAULT (datetime('now')),
    read_at   TEXT
);
CREATE INDEX idx_msg_recipient ON messages(recipient, sent_at DESC);
CREATE INDEX idx_msg_pair      ON messages(sender, recipient, sent_at);
```

Conversations derived: "chat with kendra" is `WHERE (sender=me AND recipient=kendra) OR (sender=kendra AND recipient=me) ORDER BY sent_at`.

### URL structure

- `/crew/<user>` - profile page (public)
- `/crew/` - roster index
- `/crew/messages` - own inbox (Remote-User determines whose)
- `/crew/messages/<contact>` - thread with contact
- `POST /crew/messages/<contact>` - send message (form POST, redirect back)
- `GET /crew/api/unread-count` - JSON, `{"unread": N}` for nav widget
- `GET /crew/api/thread/<contact>?after=<id>` - JSON, for future SSE/polling refresh

### Inbox page

- List of conversations, one row per contact
- Row shows: contact avatar + name + last message preview + timestamp + unread count badge
- Sorted by last-message time desc
- Click row → thread view

### Thread page

- Header with contact name + link to their profile
- Chronological messages (oldest top, newest bottom)
- Own messages right-aligned amber; contact's left-aligned cyan
- Compose form at bottom: textarea (max 2000 chars) + SEND button
- Enter = newline; button submits
- On page load: mark all incoming messages in this thread as read; auto-scroll to bottom

### "SEND MESSAGE" from other's profile

Button on `/crew/<other>` links to `/crew/messages/<other>` with focus on compose textarea.

### Access + limits

- Any voidauth-authed user can DM any other voidauth-authed user
- No block list in MVP
- Soft rate limit: 100 messages/hour/sender (in-memory counter)

### Notifications - MVP

- In-app badge on nav widget (same-origin polling)
- **Deferred:** ntfy push (opt-in per user via `crew_users.ntfy_topic` field), SSE/SocketIO real-time thread updates

## Admin app (`ishimura-admin`)

Small Flask app at `127.0.0.1:8088` serving `/admin/*`.

**Auth:** `before_request` handler reads `Remote-Groups`, returns 403 with "INSUFFICIENT CLEARANCE" page (same aesthetic as existing tailnet-off page) unless `admin` group is present.

**Routes:**

- `GET /admin/` - dashboard with service tiles
- `GET /admin/health` - detailed health status

**Content:**

- Tiles for existing admin-linked services: tdarr, grafana, prometheus, scrutiny, ntfy, adguard, slskd, pelican
- Health status dots reuse existing `/health/*` routes (already in `pangolin.nix`)
- Same theme as rec deck and crew for visual consistency

**Individual service auth:**

Each linked service (tdarr, grafana, prometheus, scrutiny, adguard, slskd) **keeps its own `tailnet-only` middleware** for now. The admin PAGE is voidauth-role-gated but the individual services stay tailnet-locked. Tightening those to voidauth roles is a per-service audit deferred to a followup.

## Error handling

- Cross-service HTTP fetches: 2s timeout, try/except, failure renders `// UNAVAILABLE` in that section
- Missing target user in URL: 404 with "CREW MEMBER NOT FOUND"
- Non-admin at `/admin/*`: 403 with "INSUFFICIENT CLEARANCE"
- Failed message send: form re-renders with error banner
- Bad message body (empty, >2000 chars): 400 with inline validation
- Rate-limited message send: 429 with "SLOW DOWN" message

## Testing

- pytest unit tests: message send/receive/thread logic with temporary SQLite
- pytest unit tests: group-check helper for admin gate
- Manual integration verification: spin games + stats + crew locally, walk through page loads
- No CI - matches existing ishimura pattern (production deploy is manual via colmena)

## Data model summary

**Crew app SQLite** (`/persist/crew/crew.db`):
- `crew_users` - identity cache (member-since, last-active, avatar, custom title)
- `messages` - DMs

**Admin app** - no DB (renders over existing `/health/*` routes)

**Cross-service reads:**
- Games hub `games.db` - via `games:5001/api/user/*/dossier` (existing)
- Stats service `stats.db` - via new `stats:5005/api/user/*/summary` + `/recent`

## Rollout phases

**Phase 1 - Nav widget + crew profile page** (~2 days)
- Build `ishimura-crew` Flask app with `/crew/<user>`, `/crew/`, `/crew/api/whoami`
- Cross-service data fetch (add new stats endpoints)
- Nav widget served from crew app
- Meta tags + script tag added to rec deck, stats, requests, refinery, static homepage, avatars page
- **Ships:** browsable crew profiles, avatar button everywhere. No messaging, no admin absorption

**Phase 2 - Messaging** (~1-2 days)
- Add messages table + inbox/thread routes/POST
- Unread badge polling in nav widget (same-origin only)
- **Ships:** DMs end-to-end

**Phase 3 - Admin absorption** (~1 day)
- Build `ishimura-admin` Flask app with `/admin/*` routes
- Migrate admin tiles + health check display from static
- Voidauth group-check middleware
- Update `pangolin.nix`: `/admin/*` → new app, remove `tailnet-only`
- **Ships:** admin off-tailnet with voidauth role gating

**Phase 4 - Enhancements (deferred, individually optional)**
- Ntfy push notifications for new messages (opt-in)
- SSE or SocketIO real-time thread updates
- Cross-subdomain unread badge (CORS + cookie sharing)
- Custom titles / cosmetics store integration
- Achievement display grid
- Voidauth OIDC integration for user avatars (replace dicebear default)
- Traefik body-rewrite injection for third-party services (Jellyfin/etc.)

Each phase is independently shippable and doesn't block the next.

## Nix module structure

```
config/crew/
  app.py           # Flask app
  db.py            # SQLite schema + helpers
  templates/
    base.html
    profile.html
    roster.html
    messages_inbox.html
    messages_thread.html
    404.html
  static/
    css/crew.css
    js/nav-widget.js  # served at ishimura.lol/nav-widget.js
    js/thread.js

config/admin/
  app.py
  templates/
    base.html
    dashboard.html
    403.html
  static/
    css/admin.css

config/ishimura_shared/
  voidauth.py      # Remote-User/Remote-Groups parsing, group-check helper
  avatar.py        # dicebear URL builder
```

Nix modules:
- `modules/nixos/normandy/crew.nix` - systemd service `ishimura-crew`, port 8087
- `modules/nixos/normandy/admin.nix` - systemd service `ishimura-admin`, port 8088
- `modules/nixos/normandy/pangolin.nix` - add routers for `/crew/*` and `/admin/*`, remove `tailnet-only` from admin router

Persistence:
- `/persist/crew/crew.db` - crew app database
- No new sops secrets (relies on voidauth headers only)

## Open questions punted to implementation

- Exact widget CSS: pill shape, corner radius, size on mobile
- Exact dicebear style (bottts vs personas vs avataaars) for default avatars
- Notification badge visual: red dot vs number vs pulsing
- Roster page (`/crew/`) sort order: alphabetical vs last-active
- Whether to show viewer's own DM history in the inbox or hide their own outbox

These get answered during Phase 1 implementation - they don't shape the architecture.

---

## 2026-07-08 restructure - crew-hub concerns split across services

Original doc envisioned a single `ishimura-crew` Flask app owning profile pages + nav widget + messaging + admin. That's now split by concern:

- **Stats owns profile pages, achievements, gamerscore, Now Playing, roster, taste profiles.** Profile page content is fundamentally stats data - stats already has the event log, adds `/crew/<user>` rendering + achievement engine + ranks. See `2026-07-09-stats-extension-design.md`.
- **Homepage owns the nav widget + roster listing URL + messaging.** Static homepage grows a small Flask overlay for `/crew/*` routing and `/msg/*` for DMs. Nav widget serves from ishimura.lol root for stable URL.
- **Bridge owns the admin console + control panel entirely.** Deletes the `/admin` router's `tailnet-only` gate and folds admin into a group-gated portion of Bridge. See `2026-07-09-bridge-design.md`.

The below sections remain accurate as design intent - just distribute their implementation across the three services above rather than one `ishimura-crew` app.

## Phase 2 (superseded - see stats extension) - Gamerscore + achievements

Adds an Xbox 360-style profile progression system driven by real usage data. Everything reads existing signals already in stats; no new event pipeline needed.

### Rank tiers

Points-based ladder with Dead Space-themed titles:

| Points | Rank |
|---|---|
| 0-99 | Maintenance Crew |
| 100-499 | Systems Technician |
| 500-999 | Flight Specialist |
| 1000-2499 | Senior Engineer |
| 2500-4999 | Bridge Officer |
| 5000-9999 | Deck Commander |
| 10000+ | Captain |

Rank shown next to username on profile + roster + nav widget dropdown.

### Achievement engine

Achievements defined in a YAML file loaded at startup (not hardcoded, not user-editable). Background job every 30 min queries stats' event log, checks each user against each achievement's condition, unlocks new ones + updates progress on tiered ones.

Achievement definition schema:

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
    description: "Watched 10+ hours in a single day"
    points: 50
    category: video
    condition:
      source: jellyfin
      metric: max_daily_hours
      threshold: 10
```

Categories: `video` (Jellyfin), `music` (Navidrome/successor), `games` (RomM + Rec Deck + Hangar), `books` (BookLore), `cross` (multi-service), `lifestyle` (time-of-day patterns, streaks), `social` (interactions with other crew).

Sample achievement types worth authoring on Phase 2 ship:

- **Threshold**: watched N hours, played N songs, read N books
- **Streak**: active every day for 7/30/100 days (tiered)
- **Diversity**: watched content in 10 genres, played games on 5 platforms
- **Repeat**: same song 50 times, same movie 3 times, same game 100 hours
- **Time-of-day**: 50%+ activity between 10PM-4AM ("Night Owl")
- **Cross-service**: active in 4/6 services in the same week
- **Social**: watched the same movie as another user within 24h ("Crew Bond"), 50%+ genre overlap ("Taste Match"), 3+ users streaming simultaneously ("Party Mode")

### Schema

Additions to `crew.db`:

```sql
CREATE TABLE achievements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    points INTEGER DEFAULT 0,
    category TEXT NOT NULL,
    parent_id TEXT,          -- for tiered achievements
    tier INTEGER DEFAULT 0,
    threshold REAL
);

CREATE TABLE user_achievements (
    username TEXT NOT NULL,
    achievement_id TEXT NOT NULL,
    unlocked_at TIMESTAMP,
    progress REAL DEFAULT 0,  -- 0.0-1.0
    PRIMARY KEY (username, achievement_id)
);

CREATE TABLE user_scores (
    username TEXT PRIMARY KEY,
    gamerscore INTEGER DEFAULT 0,
    rank_title TEXT DEFAULT 'Maintenance Crew',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Profile page additions

- Gamerscore + rank prominently in the header ("Chief Engineer :: 4,280 pts")
- Recent achievements block (last 5 unlocked, with dates)
- Achievement showcase grid (opt-in - pick 6 favorites to highlight)
- Full achievements page at `/crew/<user>/achievements` with progress bars for locked-but-in-progress ones
- Leaderboard link (aggregated across crew)

### Leaderboards

`/leaderboard` renders rankings by:

- Total gamerscore
- Per-category scores (video, music, games, books)
- Monthly + weekly activity
- Achievement count
- Specific metrics (most watch hours, most songs)

Weekly-reset section for time-limited competition.

### Toast notifications

New unlock triggers:

- Push via existing ntfy topic for the user
- Post to Discord via the Comms Officer bot
- Toast on next page load across ishimura services (nav-widget already loaded on every page, add a small unread-achievement badge + toast slot)

### Now Playing status

Real-time presence on profile + roster + nav widget:

- Jellyfin `/Sessions` API for active video streams
- Navidrome/successor Subsonic API for current music
- Hangar `/public/status` for game server presence
- Rec Deck live match state

30s polling from crew Flask app, cached, exposed at `/crew/api/now-playing/<user>`.

## Phase 3 - Weekly + monthly challenges

Time-limited bonus point events, either admin-curated or auto-generated.

```sql
CREATE TABLE challenges (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    points INTEGER,
    start_date DATE,
    end_date DATE,
    condition_json TEXT
);

CREATE TABLE user_challenges (
    username TEXT NOT NULL,
    challenge_id TEXT NOT NULL,
    progress REAL DEFAULT 0,
    completed_at TIMESTAMP,
    PRIMARY KEY (username, challenge_id)
);
```

Auto-generated examples: "Horror Week - watch 5 horror movies this week (+50)", "Album Explorer - listen to 10 full albums this month (+75)". Cross-post to Discord + newsletter.

## Phase 4 - 3D avatars (evolution of `avatars.ishimura.lol`)

Replace/complement the current 2D DiceBear + upload avatars with interactive 3D models on profile pages. Old-projects prototype at `notes/old-projects/data/avatars/` had DB + SVG cache; this phase supersedes it.

### Approach

Three.js renders low-poly modular character models client-side. Base body + swappable equipment slots (head, suit, helmet, gloves, boots, accessory, weapon). Achievement-gated cosmetics per slot.

### Schema

```sql
CREATE TABLE avatar_config (
    username TEXT PRIMARY KEY,
    model_base TEXT DEFAULT 'crew_default',
    head TEXT,
    suit TEXT DEFAULT 'standard_rig',
    helmet TEXT,
    gloves TEXT,
    boots TEXT,
    accessory TEXT,
    weapon TEXT,
    colors_json TEXT,
    pose TEXT DEFAULT 'standing'
);

CREATE TABLE avatar_items (
    id TEXT PRIMARY KEY,
    slot TEXT NOT NULL,
    name TEXT NOT NULL,
    model_file TEXT NOT NULL,  -- GLTF path
    thumbnail TEXT,
    unlock_condition TEXT,     -- achievement_id or gamerscore threshold
    rarity TEXT DEFAULT 'common'
);
```

### Sample unlock ladder

| Item | Slot | Unlock |
|---|---|---|
| Standard RIG | Suit | default |
| Advanced RIG | Suit | 1000 gamerscore |
| Elite RIG | Suit | 5000 gamerscore |
| Isaac's Helmet | Helmet | 10000 gamerscore |
| Plasma Cutter | Weapon | "Century Viewer" achievement |
| Headphones | Accessory | "Playlist Royalty" achievement |
| Reading Glasses | Accessory | "Bookworm" achievement |
| Gamepad Pin | Accessory | "Multi-Platform" achievement |
| Night Vision Goggles | Helmet | "Night Owl" achievement |
| Fire Badge | Accessory | "Binge Watcher" achievement |

### Editor

Full-screen customizer at `/crew/<self>/customize`:

- Slot tabs (Head / Suit / Helmet / Accessories / Weapon / Colors)
- Grid of available items per slot; locked ones grayed with unlock requirement shown
- Live 3D preview as items swap
- Color picker per slot
- Pose selector (standing, sitting, action)

### Static export

Server-side render a static PNG of the current avatar pose for:

- Open Graph card at `/crew/<user>/card.png` for shareable previews
- Jellyfin sync (avatar-sync script pushes the rendered PNG)
- Nav widget avatar image

Rendering happens once on avatar-config change, cached. Uses headless Three.js via node-canvas or a small Puppeteer job scheduled after edits.

## Phase 5 - Comparisons + social layer

- Side-by-side stats between two users (`/crew/compare/<a>/<b>`)
- Genre overlap Venn diagram
- Achievement race view (who's closer to the next tier?)
- Friend framework - `friendships` table for future gating of activity feeds when the crew grows past household size
- Ping/nudge: quick "hey watch this with me" prompt to another user (routes through messaging)

## Non-goals for the profile system

- Not full character faces/animation - low-poly modular is enough
- Not micro-transactions (obviously)
- Not exposed to public web unauthed - all profile data requires voidauth session
- Not gamification of every action - some services (voidauth admin, hangar power controls) don't need points

## Data pulled from where

| Signal | Source |
|---|---|
| Watch hours, watch history | stats (Jellyfin webhook) |
| Song plays | stats (Navidrome/successor scrobble) |
| Books read | stats (BookLore integration) |
| ROMs played | stats (RomM integration) |
| Rec Deck matches | games service |
| Game server presence | hangar `/public/status` |
| Achievement progress | derived from stats event log by crew app |
| Rank + gamerscore | computed by crew app, cached |
| Now Playing | polled from service APIs (Jellyfin /Sessions, Subsonic, hangar, games) |
