# Ishimura Bridge - Homelab Control Panel Design (`bridge.ishimura.lol`)

**Status:** design brainstormed 2026-07-09, ready for scope-cut + implementation planning.

**One-liner:** Unified admin control panel for the ishimura + nostromo + normandy homelab. Systemd unit control across hosts, real-time logs, host system metrics, service health, audit trail, alerts, and pre-approved command buttons. Replaces the current `ishimura.lol/admin` static page + fills the ops-visibility gap that Grafana doesn't cover well.

**Why:** Grafana is great for time-series but bad at "start/stop this thing". Hangar is game-only. The current `/admin` page is a link list. A dedicated control panel that owns fleet-wide ops (mutating actions with audit trail, alerts, quick commands) gives us the Pelican-adjacent power we lost when we retired Pelican, without the container-management complexity.

## Guiding principles

- **Every mutating action goes through Bridge and lands in Captain's Log.** Complete audit trail.
- **Nothing arbitrary.** No shell terminal, no `docker exec`. Only pre-declared YAML commands + systemd verbs on whitelisted units.
- **Read-only where possible.** Log viewer, stats sparklines, health pings need zero privileges.
- **Fleet view, not host view.** ishimura + nostromo + normandy all appear in one UI. Cross-host actions dispatch via SSH-over-tailnet with keyed sudo.
- **No interactive ship schematic.** Tried it before, felt like bloat. Deck-plan card grid is enough.
- **Complementary to Hangar, not overlapping.** Hangar owns game servers (start/stop/config/mods/players). Bridge owns everything else + fleet-level operations. Bridge can reach into Hangar's `/public/status` for read; game-server power controls stay in Hangar's UI.

## Non-goals

- Not a Podman/Docker manager (we're nix-native systemd; podman only runs tdarr-node)
- Not a shell/exec surface (declared commands only)
- Not a replacement for Grafana (metrics dashboards stay there)
- Not multi-user with per-service permissions (admin group = full access, not-admin = no access, MVP)
- Not host provisioning (nix rebuild flows stay on the CLI)
- Not an interactive ship-map view (deck grid is enough)

## Architecture

### Hosting

Flask app on normandy (the VPS ingress). Chosen because:

- Normandy already fronts every service via pangolin/traefik
- SSH into ishimura + nostromo happens over tailnet, so normandy needs to reach them anyway
- Keeps ishimura + nostromo focused on their primary roles (media/games)

Configuration:

- `bridge.ishimura.lol` behind pangolin + voidauth-forwardauth requiring `admins` group
- Runs as `bridge` systemd user, port `5015`
- Nix module at `modules/nixos/normandy/bridge.nix`
- Persistence at `/persist/bridge/` for SQLite + user prefs
- SSH keyed via sops secret `bridge/ssh_key` with a `NOPASSWD` sudo entry on target hosts limited to the whitelisted verbs (`systemctl start|stop|restart` on managed units)

### Fleet reach

Bridge dispatches actions to remote hosts via a small daemon on each managed host (`bridge-agent`) OR direct SSH. Decision matrix:

- **SSH-based dispatch** - simplest, uses existing tailnet + SSH infra, sudo whitelist limits blast radius. MVP.
- **Bridge-agent daemon** - each host runs a small HTTP receiver; Bridge posts JSON commands. Cleaner but more moving parts. Phase 3.

Start with SSH. Migrate to agent daemons when the SSH latency (~200ms per call) becomes annoying.

## Data model

```sql
-- The audit trail. Every mutating action lives here.
CREATE TABLE captains_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,           -- Remote-User from voidauth
    action TEXT NOT NULL,             -- "start", "stop", "restart", "cmd:kf2-restart-clean", "ack:alert:47"
    target TEXT NOT NULL,             -- "ishimura:jellyfin.service", "nostromo:kf2.service"
    result TEXT NOT NULL,             -- "success", "error", "denied", "timeout"
    detail TEXT,                      -- error message, response snippet
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_log_time ON captains_log(created_at DESC);
CREATE INDEX idx_log_user ON captains_log(username);
CREATE INDEX idx_log_target ON captains_log(target);

-- Alerts with acknowledgement
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    severity TEXT NOT NULL,           -- "red" (down), "yellow" (degraded), "green" (recovered)
    source TEXT NOT NULL,             -- "ishimura:jellyfin", "system:disk_full"
    message TEXT NOT NULL,
    acknowledged BOOLEAN DEFAULT 0,
    acknowledged_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP
);
CREATE INDEX idx_alerts_active ON alerts(acknowledged, severity);

-- Historical host system stats (host-level, not per-unit - hangar owns per-game-server stats)
CREATE TABLE host_stats_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT NOT NULL,               -- "ishimura", "nostromo", "normandy"
    cpu_percent REAL,
    mem_percent REAL,
    mem_used_gb REAL,
    disk_percent REAL,
    disk_used_gb REAL,
    gpu_percent REAL,
    gpu_mem_percent REAL,
    gpu_temp_c REAL,
    load_1 REAL,
    load_5 REAL,
    load_15 REAL,
    net_rx_mbps REAL,
    net_tx_mbps REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_host_stats ON host_stats_history(host, recorded_at DESC);

-- Per-user preferences
CREATE TABLE user_prefs (
    username TEXT PRIMARY KEY,
    default_view TEXT DEFAULT 'deck',   -- "deck" | "log" | "vitals"
    compact_mode BOOLEAN DEFAULT 0,
    subscribed_alerts TEXT              -- JSON array of source patterns to push
);
```

Retention: `captains_log` keeps 90 days rolling then archives to compressed monthly files in `/persist/bridge/logs/`. `host_stats_history` keeps 24h at 30s + 30d at 5min downsampled + discard.

## Sections

Deck-plan card grid. Each deck is a category of services + hosts.

### Command Deck (Auth, routing, ingress)

- voidauth
- pangolin/traefik on normandy
- crowdsec
- dns / adguard

Each card: name, health dot, uptime, quick action buttons (restart), link to service.

### Media Deck

- jellyfin
- navidrome (or successor)
- booklore
- romm
- refinery
- rec deck / games

### Hangar Deck

Read-only reflection of hangar's servers (KF2, VS, Tarkov-SPT). Player counts, uptime. Deep links into Hangar for actual control - Bridge doesn't duplicate game-server controls. Just visibility.

### Ops Deck

- ntfy
- grafana + prometheus
- Loki (if we add it)
- tdarr

### Infrastructure Deck

Host-level cards for ishimura + nostromo + normandy:

- CPU/mem/disk/net gauges + 24h sparklines
- Uptime, load averages
- GPU utilization + temp (nostromo/ishimura)
- Storage: mnt/storage per-disk usage, NFS capacity, mergerfs branch balance
- Recent kernel messages if anything noteworthy

## Feature surfaces

### Systemd unit control

For every whitelisted unit:

- `start` / `stop` / `restart` / `reload` buttons
- `journalctl -u <unit> -n 200` "peek logs" popover
- Confirmation modal for critical units (voidauth, pangolin, sshd, caddy on normandy)
- All actions log to Captain's Log with username + host + target + result

Unit list declared per-host in `modules/nixos/<host>/bridge-units.nix`, merged at build time into `/etc/bridge/units.json`. Never controlled from the UI directly.

### Real-time log tail

For any unit: SSE-based stream of `journalctl -u <unit> -f -o cat`. Same pattern as Hangar's log viewer:

- Scrollback + follow-tail + pause-on-scroll
- Clear button
- ANSI strip (already implemented in Hangar - lift the regex)
- Cross-host log tail via SSH + streaming stdout

### Command buttons (OliveTin-style)

Pre-defined admin commands as YAML, safer than shell exec:

```yaml
commands:
  - id: renew-porkbun-certs
    label: "Force renew Porkbun certs"
    host: normandy
    steps:
      - systemctl: reload traefik
    confirm: true

  - id: refinery-scan-now
    label: "Trigger Refinery scan"
    host: ishimura
    steps:
      - curl: "http://127.0.0.1:5006/_scan"
    confirm: false

  - id: rebuild-jellyfin-cache
    label: "Rebuild Jellyfin metadata cache"
    host: ishimura
    steps:
      - systemctl: stop jellyfin
      - rm: /var/lib/jellyfin/cache
      - systemctl: start jellyfin
    confirm: true
    danger: true

  - id: nostromo-restart-nm
    label: "Restart NetworkManager (nostromo)"
    host: nostromo
    steps:
      - systemctl: restart NetworkManager
    confirm: true
```

Commands live in `modules/nixos/normandy/bridge-commands.nix`. Only YAML-declared commands are runnable. Every command logs to Captain's Log.

UI: chip list on the relevant deck. `confirm: true` triggers a modal. `danger: true` styles the chip red.

### Captain's Log viewer

`/log` page:

- Paginated table: timestamp, user, host:target, action, result
- Filter by user, action pattern, host, target, date range
- Full-text search on `detail` field
- Colored severity: green = success, yellow = timeout/partial, red = error/denied
- Export filtered view as JSONL

### Alerts

Sourced from:

- Health probes (Bridge pings each service's `/health` or `/healthz` every 30s)
- Host stats collector (CPU > 90% sustained 5min → yellow, disk > 90% full → yellow, etc.)
- systemd unit state monitoring (unit went to `failed` → red)
- Hangar's `/public/status` for game-server presence
- Prometheus alertmanager webhook (if configured, incoming alerts route here)

Alert lifecycle: created → surfaces as red/yellow banner on Bridge homepage + push to ntfy + cross-post to Comms Officer Discord bot → user acks (writes ack to Captain's Log) → moves to acknowledged state → auto-recovers to green when condition clears → auto-archives after 24h in green.

### Health check pings

Cheap. Every 30s:

- For services with a health endpoint: GET, check 200
- For units without: `systemctl is-active <unit>` via SSH
- Latency logged per probe (kept as recent-N samples for the sparkline)

### Host system stats

Collector runs on each host (small Python script or existing node_exporter parsed):

- `/proc/loadavg`, `/proc/meminfo`, `/proc/net/dev`
- `sensors` output (temps)
- `nvidia-smi` (nostromo + ishimura GPU)
- `df -B1` on important mounts
- mergerfs per-branch stats via `mergerfs.dup`

Pushed to Bridge every 30s via HTTP POST from each host to `bridge.ishimura.lol/api/host-stats`. Bridge stores + serves for sparklines.

### Storage view

Special panel dedicated to `/mnt/storage` (the mergerfs union on ishimura):

- Per-library folder size (music, movies, shows, anime, books, roms) as a treemap
- Per-disk (disk1, disk2) usage bars
- mergerfs branch balance visualization
- Downloads folder size trend (spotting stuck downloads)

## Ntfy alert routing

Users configure which alert sources they subscribe to. Default subscriptions:

- Admins: everything
- Non-admins: nothing (they shouldn't have Bridge access anyway)

Push flow: alert created → user subscribed → ntfy POST with `Priority`, `Tags`, `Title`, body. Tags map severity to icon (red = 🚨, yellow = ⚠️, green = ✅ recovered).

## Auth

- `admins` group (via voidauth) required for all Bridge routes
- Read-only surfaces (log viewer, Captain's Log) allowed for `admins` only in MVP
- Future: `operators` group with view-only access + ack-alerts permission

## Techstack

- Python + Flask + APScheduler + SQLite
- Paramiko for SSH dispatch to remote hosts (later migrated to a bridge-agent daemon)
- Server-rendered HTML with light JS (uPlot for sparklines, alpine.js or plain JS for interactive bits)
- Nix module + sops for SSH key + any per-service tokens

## Stages

### Stage 1 - MVP (1 week)

- Flask app + auth + `bridge.ishimura.lol`
- Unit whitelist mechanism
- Deck-plan card grid pulling health status
- Start/stop/restart for whitelisted units on all 3 hosts via SSH
- Captain's Log persistence + `/log` viewer
- Real-time log tail SSE (single unit at a time)
- Host stats collector on each host + 24h sparklines

Deliverable: replaces the current `/admin` page with a real ops surface.

### Stage 2 - Commands + alerts (1 week)

- Command YAML + declared-command execution
- Health probe scheduler + alerts pipeline
- Ntfy integration
- Alerts UI + ack flow
- Storage view

### Stage 3 - Bridge-agent daemon (optional, 3-5 days)

- Small HTTP receiver on each host
- Bridge posts JSON commands instead of SSH
- Better latency, simpler audit at receive-time

### Stage 4 - Polish (3-5 days)

- Per-user subscription preferences
- Cross-post alerts to Comms Officer Discord bot
- Grafana alertmanager webhook receiver
- Loki integration for log search across hosts (if we adopt Loki)

## Data sources

| Signal | Source |
|---|---|
| Unit state | `systemctl is-active` via SSH |
| Unit logs | `journalctl -u <unit> -f` via SSH |
| Host CPU/mem/net | `/proc/*` collector on each host |
| GPU | `nvidia-smi` |
| Disk usage | `df -B1` + `du -sB1` |
| Service health | each service's `/health` endpoint |
| Hangar state | Hangar `/public/status` |
| Prometheus alerts | alertmanager webhook |

## Ties into

- [[hangar]] - Bridge reads Hangar's `/public/status` for game server presence; delegates game-server power controls to Hangar's UI
- [[stats]] - user profile pages live in stats; Bridge doesn't overlap
- [[daily]] - Bridge alerts can trigger Special Editions in the daily newspaper
- [[comms officer]] - Bridge alerts cross-post to Discord via the bot
- Existing homepage `/admin` router - deleted from pangolin.nix once Bridge is up (its `tailnet-only` gate goes away, Bridge takes over)

## Non-goals (revisited)

- Not building the interactive ship-map view (deck grid is enough)
- Not deep container introspection (podman/docker inspect not needed; only tdarr-node runs in podman)
- Not a package upgrade UI (nix flake update stays CLI)
- Not password/secret rotation UI (sops workflow stays CLI)

## Open questions

- **Fleet dispatch: SSH vs agent** - MVP is SSH; migrate to bridge-agent if latency becomes annoying (~200ms per call adds up during bulk operations)
- **Prometheus alertmanager wiring** - do we forward all Prom alerts to Bridge or just critical? Probably a labeled filter
- **Alert acknowledgement scope** - does ack silence future re-alerts of the same condition? Simplest MVP: ack applies to current alert instance only, re-fires if condition recurs
- **Storage view treemap library** - vanilla SVG or a small lib? Probably vanilla to keep bundle small
