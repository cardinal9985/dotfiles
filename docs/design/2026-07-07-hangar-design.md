# Hangar - Custom Game Server Control Panel

**Status:** Stages 1-7 shipped as of 2026-07-08. Pelican retired end-to-end - all three games (KF2, Vintage Story, SPT/Tarkov) run native under Hangar. Backups timer + full mods panel remain (formerly Stages 8-9, now Stages 8-10 - see below). See "Post-spec deliveries" for work added on the fly.

**One-liner:** Replace Pelican + Wings with a nix-native game-server stack: one nix module per game (systemd services running the binary directly), one Flask control-plane (`hangar.ishimura.lol`) exposing status/logs/console/mods, and voidauth in front. Migrates KF2, Vintage Story, and SPT/Tarkov off Pelican for good.

**Why:** The Wings + Podman attach-500 bug (spent hours chasing, never resolved) proved Pelican isn't a stable foundation on NixOS. Every other service on ishimura is Flask + systemd + nix; Pelican is the odd one out. Going native means: no runtime mystery, saves and configs live at grep-able paths, systemd handles restart/logs/limits, and the panel can integrate cleanly with the rest of the ecosystem (crew hub, tickets, achievements) instead of siloed.

---

## Architecture

### Volume layout

```
/persist/gameservers/
├── kf2/                 (KF2 files - migrated from /var/lib/pelican/volumes/<uuid>/)
├── vintagestory/        (VS world + config)
├── tarkov-spt/          (SPT profiles + mods)
└── ...                  (per-game subdir, self-documenting)
```

`/persist/` matches the ishimura impermanence convention - survives root wipes. Backup timers walk this tree. Migration from Pelican = same-filesystem `mv`, atomic, free.

### Per-game nix module contract

Every game server is a small (~40-80 line) module at `modules/nixos/nostromo/gameservers/<name>.nix` that:

1. Declares a systemd service running the game binary (usually via `steam-run`)
2. Uses sops for secrets (admin password, API keys, RCON pass)
3. Sets `Restart=on-failure`, `LimitNOFILE=1048576`, resource limits
4. Owns files under `/persist/gameservers/<name>/` as the `pelican` user (kept for compat / mv simplicity; can rename later)
5. Emits a discovery file at `/etc/hangar/servers.d/<name>.json` describing itself for Hangar to find

Example discovery file (`vintagestory.json`):

```json
{
  "slug": "vintagestory",
  "name": "Vintage Story",
  "systemd_unit": "vintagestory.service",
  "volume": "/persist/gameservers/vintagestory",
  "game_type": "vintagestory",
  "connect_address": "games.ishimura.lol:42420",
  "config_files": ["config/serverconfig.json"],
  "console_backend": "vs_http",
  "mod_backend": "vs_moddb"
}
```

Hangar scans `/etc/hangar/servers.d/` on start (and on file-watch) to build its server list. No hardcoded knowledge of games in the Flask app - it's all data.

### Hangar Flask app

- **Path:** `config/hangar/` (mirrors other custom apps like refinery, requests, games)
- **Deploy:** nix module at `modules/nixos/nostromo/hangar.nix`
- **Port:** 5010 (local), fronted by pangolin as `https://hangar.ishimura.lol`
- **Auth:** voidauth-forwardauth middleware, `admin` group required
- **Runs on nostromo** (same host as game servers, so systemd D-Bus + journalctl work directly)

Routes:

```
GET  /                        server list (name, status dot, quick actions)
GET  /server/<slug>            server detail: status card, log tail, controls
POST /server/<slug>/power      body: {"action": "start|stop|restart"}
GET  /server/<slug>/log        SSE stream of journalctl -u <unit> -f
POST /server/<slug>/command    body: {"command": "..."}  (routed to game-specific backend)
GET  /server/<slug>/config     read config file (whitelist from discovery)
POST /server/<slug>/config     write config file
GET  /server/<slug>/mods       server-specific mods tab
POST /server/<slug>/mods/install
POST /server/<slug>/mods/remove
GET  /api/servers              JSON list for homepage/other integrations
GET  /api/server/<slug>/status JSON status (up/down/players/uptime)
GET  /healthz
```

Systemd interaction via `python-systemd` bindings (D-Bus) or `subprocess.run(["systemctl", ...])` - probably start with subprocess for simplicity, upgrade to D-Bus later if we want structured properties.

Live console = SSE endpoint that spawns `journalctl -u <unit> -f -n 200 -o cat` and streams stdout line-by-line as `data: ...` events. Client-side is a scrollback view with ANSI stripping.

### Console command backend abstraction

Different games have different admin-command surfaces. Encoded per-game:

| Game | Backend | Notes |
|-----|-----|-----|
| KF2 | WebAdmin HTTP POST | Session cookie auth, POST to `/ServerAdmin/current+console` |
| Vintage Story | HTTP `/api/server/console/execute` | Requires admin token from server config |
| SPT / Tarkov | Not applicable | SPT doesn't expose runtime console; readonly panel |
| Future games | plugin per game | Same interface |

Interface (Python):

```python
class ConsoleBackend:
    def send(command: str) -> str  # returns output or empty
    def can_send() -> bool
```

Discovery file's `console_backend` field selects which class instantiates.

### Mods panel

Per-game plugin that implements a common `ModSource` interface:

```python
class ModSource:
    def search(query: str, page: int) -> list[Mod]
    def get(mod_id: str) -> Mod  # detail: versions, description, changelog
    def install(mod_id: str, version: str | None) -> None
    def list_installed() -> list[InstalledMod]
    def remove(mod_id: str) -> None
    def check_updates() -> list[UpdatedMod]
```

Per-game implementations:

| Game | Source | Browse | Install | Notes |
|-----|-----|-----|-----|-----|
| Vintage Story | moddb.vintagestory.at JSON API | ✅ | ✅ via `/moddb install` console cmd | Existing HTML already implements this |
| KF2 | Steam Workshop API (public, requires WEB_API_KEY) | ✅ | ✅ via `steamcmd +workshop_download_item 232090 <id>` | Edit `KFEngine.ini` `ServerPackages=` on install |
| SPT / Tarkov | hub.sp-tarkov.com RSS feed + scrape | ⚠️ browse via RSS titles + link scrape | ✅ file drop into `user/mods/<mod-slug>/` | Client-side mods still need players to grab a zip; that's what today's `mods.zip` covers |

UI: existing `config/mods/index.html` (VS-specific) gets ported into Hangar as the base mods-tab template. API paths rewired: `/api/pelican` → `/api/server/<slug>/*`, `/api/wings` websocket → `/api/server/<slug>/log` SSE, `/api/moddb` proxy stays. Per-game plugins swap in different data sources but keep the same shell.

### Homepage integration

- `hangar` service card on ishimura.lol home page (services grid), voidauth-gated
- Existing per-game tiles on the games section pull status from `hangar.ishimura.lol/api/server/<slug>/status` instead of `pelican.ishimura.lol` API
- Deprecate `game-status-poller` systemd unit on normandy - hangar becomes the source of truth for game-server state

### Backups

`systemd.timers.hangar-backup` on nostromo:

- Runs weekly (or configurable per server via discovery file)
- Uses `borg` (deduplicated, incremental) writing to `/persist/backups/gameservers/`
- Per-server archive names: `<slug>-YYYY-MM-DD-HHMM`
- Hangar UI has a Backups tab per server: list snapshots, "run backup now" button, "restore" opens a confirm dialog (nuke + restore is destructive - always confirm)
- Retention: last 4 weekly + last 3 monthly, prune via `borg prune`

### Loss vs Pelican - honest inventory

| Pelican feature | Hangar handles it? |
|-----|-----|
| Start/stop/restart | ✅ systemctl |
| Live console output | ✅ journalctl SSE |
| Send admin commands | ✅ per-game backend (KF2 WebAdmin API, VS HTTP API) |
| Web file manager | ❌ Use SSH + $EDITOR. Optional read-only file browser later. |
| Backups | ✅ borg + timer + UI |
| Subusers with permissions | Limited: voidauth admin vs viewer groups only |
| Egg-style "add game X" | Slower: nix module + PR to dotfiles. Debuggable though. |
| Node system for multi-host | ❌ single-host (nostromo). Not needed for homelab. |
| Database provisioning | ❌ No games we run need this |

---

## Stages

**Total effort estimated at ~14-21 evenings across 9 stages; actual shipped in ~2 evenings** (2026-07-07 through 2026-07-08). Each stage was independently shippable, which held up in practice.

### Stage 1 - Volume relocation (KF2) - ✅ done 2026-07-07

Moved `/var/lib/pelican/volumes/<uuid>/` → `/persist/gameservers/kf2/`. Updated `modules/nixos/nostromo/kf2.nix` volume path. Wings-side tmpfiles trimmed.

### Stage 2 - Hangar Flask MVP - ✅ done 2026-07-07

- `config/hangar/app.py`, `shared_auth.py`, templates + static
- `modules/nixos/nostromo/hangar.nix` with polkit rules for hangar user D-Bus systemctl (no sudo)
- Discovery file at `/etc/hangar/servers.d/kf2.json`
- Pangolin route + voidauth `admins` group middleware
- Homepage tile

Two lessons: (1) `admins` (plural) is the voidauth group name, not `admin`. (2) Polkit rule beats sudo - avoids `PermissionError [Errno 13]` on `/run/wrappers/bin/sudo`.

### Stage 3 - Live console + logs - ✅ done 2026-07-07

- SSE endpoint at `/server/<slug>/log` spawning `journalctl -u <unit> -f -o cat -n 200`
- Frontend log viewer (scrollback, follow-tail, keyboard nav)
- Ship-styled terminal, no iframe
- ANSI escape stripping added later once SPT began emitting colour codes (2026-07-08)

### Stage 4 - KF2 WebAdmin progressive replacement - ✅ done 2026-07-07

Full parity with WebAdmin behind Hangar:

- `config/hangar/backends/kf2_webadmin.py` with cached session cookie + `_post_form()` helper that preserves every WebAdmin form field and auto-includes the first named submit button (`action=save`)
- Console tab, Players tab (kick/ban/mute across three separate URLs: `/policy/sessionbans`, `/policy/bans`, `/policy/ipbans`)
- Settings tab reads `settings_GameDifficulty_raw` from `/settings/general` + infers length from `gs_wave` count (4=Short/7=Medium/10=Long), caches in memory
- MOTD/welcome tab writes `BannerLink`, `ClanMotto`, `ClanMottoColor`, `ServerMOTD`, `ServerMOTDColor` (not the fields we initially guessed)
- Passwords POST to `/ServerAdmin/policy/passwords` (not `/settings/general`)
- Live difficulty/length changes go via console `SetGameDifficulty <n>` / `SetGameLength <n>` (WebAdmin's Change form kicks everyone; console commands don't)
- 5-category cheatsheet baked in

**KF2 fully replaced Pelican + WebAdmin.** The homepage WebAdmin tile is gone; the WebAdmin server stays running on `127.0.0.1:8380` for Hangar's backend to scrape.

### Stage 5 - Vintage Story migration - ✅ done 2026-07-08

- `modules/nixos/nostromo/vintagestory.nix` using `pkgs.vintagestory` (unfree)
- Volume `/persist/gameservers/vintagestory/` under hangar user
- Migrate oneshot: `.hangar-initial-config` marker guards the one-time `--setconfig="{ WhitelistMode: 'Off', AdvertiseServer: false }"`
- VS 1.22 quirk: `WhitelistMode` is a string enum ("Off"/"On"/"Blacklist"); JSON `false` serialises to `0` which the runtime silently treats as invite-only. Config now uses the string.
- `config/hangar/backends/vs_stdin.py` with:
  - `sleep infinity > FIFO` background writer keeps the pipe alive so `os.open(fifo, O_WRONLY | O_NONBLOCK)` from Hangar just works
  - `journalctl -f -o cat` tail thread + regex state machine for join/leave. Real VS 1.22 log lines: `[Server Event] MaxwellPayne [::ffff:IP]:PORT joins.` / `[Server Event] Player MaxwellPayne left.`
- Full parity with KF2: console, player list, kick/ban, cheatsheet

### Stage 6 - SPT / Tarkov migration - ✅ done 2026-07-08

- `modules/nixos/nostromo/tarkov-spt.nix` runs `steam-run ./SPT.Server.Linux` from `/persist/gameservers/tarkov-spt/`
- SPT ships as a self-contained .NET publish (libcoreclr + all System.*.dll in-tree) - no dotnet runtime dep, steam-run is enough
- Migrate oneshot: `rsync -a /var/lib/pelican/volumes/bb020144.../ ${volume}/` then chown to hangar. Preserves `user/mods/` (Fika + others), `user/profiles/`, `user/certs/`, `user/cache/`
- Discovery entry with `console_backend = "spt_journal"` (added post-Stage 6)

### Stage 7 - SPT journal-based player tracker - ✅ done 2026-07-08

Not in the original spec - added when we noticed KF2 and VS had player counts but Tarkov didn't.

- `config/hangar/backends/spt_journal.py` mirrors `vs_stdin` structure (background journalctl tail + regex state machine), minus the FIFO (SPT has no admin console worth wrapping)
- Real SPT log patterns (from live capture, case-inconsistent): `[WS] Player: <Name> (<24-hex-profile-id>) <ts> has connected` / `[ws] player: ... has disconnected`
- Known limitation: SPT drops the notifier WebSocket the instant a player enters a raid (client swaps to `/fika/update/*` HTTP polling), so `player_count` reflects "at menu / in hideout" rather than "in raid". Fine as a "someone's on" signal.
- Fika + backendIp + NAT-punch config shipped in the same window (see Post-spec deliveries)

### Stage 7b - Pelican retirement (formerly Stage 9's first half) - ✅ done 2026-07-08

- Deleted `modules/nixos/nostromo/wings.nix` and its default.nix import
- Deleted `modules/nixos/ishimura/pelican.nix` and its default.nix import + `pelican/app_key` sops entry
- Pangolin: removed `pelican-router`, `wings-router`, `pelican-service`, `wings-service`, `homepage-health-pelican-router`, `rewrite-pelican-health` middleware; removed `pelican/application_api_key` sops entry
- Homepage: dropped Pelican + KF2 WebAdmin tiles; poller descriptions rewritten to say Hangar
- Network firewall comments updated so no stale "Pelican raw resource" strings remain
- The 4.9G volume at `/var/lib/pelican/volumes/bb020144.../` is safe to `rm -rf` whenever the user is ready (SPT already moved off it, verified game runs)

### Stage 8 - Backup timer + UI - not started

Original Stage 9 second half. Still open:

- Borg-based systemd timer that snapshots `/persist/gameservers/` weekly (or per-server override via discovery file)
- Per-server archive names, retention (4 weekly + 3 monthly), `borg prune`
- Backups tab per server in Hangar: list snapshots, "run backup now", restore w/ confirm modal
- Restore-to-a-new-bay option (read-only mount) so full restores aren't scary

### Stage 9 - VS mods panel - not started

Original Stage 7. Still open:

- Port `config/mods/index.html` (VS-specific) into Hangar's per-server-mods tab template
- `ModSource` base class + `VintageStoryMods` plugin (moddb.vintagestory.at API + `/moddb install` console command)

### Stage 10 - KF2 + SPT mods panels - not started

Original Stage 8. Still open:

- `KF2Mods`: Steam Workshop API (needs `hangar/steam_web_api_key` in sops), `steamcmd +workshop_download_item 232090 <id>`, edit `KFEngine.ini` `ServerPackages=`
- `TarkovMods`: hub.sp-tarkov.com RSS feed for browse, install by extracting zip into `user/mods/<mod-slug>/`

### Stage 11 - Hardware stats per server - not started

Pelican used to show per-server CPU/memory/disk. Rebuild that as a native cgroup v2 collector.

- Background collector every 30s reads `/sys/fs/cgroup/system.slice/<unit>.service/` for each managed unit
  - `memory.current` (bytes)
  - `cpu.stat` (usage_usec, delta over collection interval)
  - `io.stat` (disk I/O per device)
  - `pids.current` (thread count)
  - Volume disk usage via `du -sB1 <volume>` (cached, refreshed every 5 min - `du` on a large game volume is expensive)
- Storage schema (SQLite in `/persist/hangar/hangar.db`):
  ```sql
  CREATE TABLE stats_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      unit TEXT NOT NULL,
      cpu_percent REAL,          -- delta / interval * 100 / cores
      mem_bytes INTEGER,
      volume_bytes INTEGER,
      io_read_bytes INTEGER,
      io_write_bytes INTEGER,
      pids_current INTEGER,
      recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE INDEX idx_stats_unit_time ON stats_history(unit, recorded_at DESC);
  ```
- Retention: 24h at 30s resolution, then downsample to 5min bins for 30d, then discard. Background job at midnight prunes + downsamples.
- Server detail page grows sparklines (24h) + gauges (current). Small chart lib (uPlot or vanilla SVG - keep it lightweight).
- Public status endpoint gains optional fields: `cpu_percent`, `mem_bytes`, `volume_bytes` so homepage tiles can show at-a-glance vitals if desired.
- One system-wide dashboard at `/vitals` shows all servers side-by-side with mini-sparklines for quick "where's the load" scanning.

### Note: cross-service ops surface lives in Bridge

Fleet-wide control panel concerns (audit trail across services, alerts, command buttons, host-level stats, container/unit control for non-game services) live in the Bridge spec, not here. Hangar stays scoped to game-server + mod concerns only. It emits events + stats that Bridge can consume, but doesn't own the ops UI.

---

## Post-spec deliveries

Things not in the original design that we built on the fly:

- **Public status endpoint** - `GET /public/status` returns `[{slug, hangar_slug, active, player_count}]` unauth over tailnet. Homepage poller on normandy hits it directly at `http://100.107.103.76:5010/public/status` bypassing pangolin/voidauth. Hangar is now the single source of truth for game-server state (poller no longer talks to Pelican API).
- **`homepage_slug` mapping** - discovery entries have both `slug` (hangar's slug) and `homepage_slug` (the homepage tile's slug); the public status endpoint maps between them so homepage tile IDs stay stable.
- **Status probe system** - `status_probe = { type = "tcp"|"http"|"process", ... }` in discovery files for pre-migration games where Hangar knew about a game but didn't run its unit. Used during the interim between Stage 4 landing and Stage 5/6 migrations.
- **Cheatsheet system** - per-backend `CHEATSHEET` list rendered in the Console tab.
- **ANSI escape stripping** - SPT emits ANSI color codes over stdout/journalctl. Log SSE strips CSI + OSC sequences before yielding, so the browser doesn't get placeholder-glyph noise. `ANSI_ESCAPE_RE = r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*(?:\x07|\x1b\\)"`.
- **Fika NAT-punch + backendIp fix** - Live edits to `/persist/gameservers/tarkov-spt/user/mods/fika-server/assets/configs/fika.jsonc`: `natPunchServer.enable: true`, `backendIp: "games.ishimura.lol"`. Nostromo firewall UDP 6790 opened (pangolin already had it). Lets Fika hosts behind NAT be joined without router forwarding. Untested with a real friend as of 2026-07-08.
- **`.hangar-initial-config` marker file** - one-time defaults on first launch (e.g. VS whitelist/advertise). Guards prevent overwriting later admin console changes.

---

## Known followups / backlog

- **KF2 WebAdmin bind to 127.0.0.1** (hardening) - WebAdmin currently listens on `0.0.0.0:8380` (tailnet-visible). Tailnet is trusted so this is marginal. The UE3 KFWeb.ini bind-address field name needs a live-config check first.
- **Old Pelican volume cleanup** - `/var/lib/pelican/volumes/bb020144.../` (4.9G) and `/var/lib/pelican/*` in general. User's call when to `rm -rf`.
- **Fika verification** - live test with a friend to confirm NAT-punch works both directions.
- **VS + SPT mod backends** - see Stages 9 + 10 above.
- **Backup timer + UI** - see Stage 8 above.

---

## Open questions to answer during implementation

- **Name inside the sops tree**: `hangar/steam_web_api_key`, `hangar/vs_admin_token`, etc. Fine to add as we go.
- **Console command backend timing**: WebAdmin for KF2 requires a logged-in session. Do we cache a session cookie server-side and refresh, or auth per-command? Cache probably.
- **SSE keepalive**: some proxies drop long-lived SSE. Pangolin's default is usually fine; if it drops, add `:heartbeat` comments every 30s.
- **Backup restore UX**: full-restore is destructive. Need a confirm modal and probably a "restore to a new bay" option (i.e. mount the borg archive read-only, don't nuke the live volume).
- **Multi-user permissions**: for now only `admin` group has access. If we ever want "viewer" (see status + logs, no controls), voidauth group check on POST routes only.
- **Migration downtime**: each game is ~30 seconds down during volume mv + `systemctl restart`. Coordinate with anyone actively playing.

---

## Ties into

- [[crew hub]] - Hangar sits under the same voidauth admin group; nav widget could show "server up/down" pill
- [[community & cross-service]] - server presence events (player joined Tarkov, VS map saved) feed the intercom bus
- [[pelican session tracking]] - obsoleted by Hangar knowing about servers directly; log-tail service moves inside Hangar
- Existing mods flow at `/mods/tarkov/mods.zip` - keeps working, served by Hangar or a sidecar

---

## Non-goals

- Multi-node / multi-host support (single nostromo, forever)
- Egg-marketplace-style "install new game type from a button" (nix modules require PRs, that's fine)
- File manager parity with Pelican (SSH is fine)
- Database provisioning UI (no games need this)
- Support for non-native game types (e.g. any game we can't run under steam-run + systemd)
