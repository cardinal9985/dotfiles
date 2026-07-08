# Ishimura Fleet Services Roadmap

**Status:** absorbed from notes/memory/project_ishimura_normandy_todo.md + project_observability_plan.md + lab-todo.md on 2026-07-09.

**One-liner:** Master roadmap of pending services + follow-ups across ishimura + nostromo + normandy. Not a spec of any single service - the source of truth for what's queued, in what rough order, with what current constraints. Individual services get their own spec docs as they enter build.

**Deploy preference:** native nixpkgs > podman container. Containerize only when no nixpkgs option exists or is significantly out of date.

## Fleet snapshot (as of 2026-07-08)

- **normandy** VPS at Servury, NYC, tailnet `100.108.98.70`, public `168.222.97.137`. Runs: pangolin, gerbil, traefik, voidauth, anubis, crowdsec LAPI, ntfy, homepage (static), certs.
- **ishimura** home server, tailnet `100.92.76.121`. Runs: jellyfin, navidrome, booklore, romm, rec deck, requests, refinery, stats, tools, tdarr server, adguard, grafana, prometheus, loki, alloy.
- **nostromo** workstation, tailnet `100.107.103.76` LAN `192.168.254.97`. Runs: hangar, kf2, vintage story, tarkov-spt, tdarr node.

Ecosystem details in `notes/memory/project_ishimura_normandy_todo.md` (this file is the summary).

## Media stack additions (Ishimura)

**Refinery arr-stack replacement** covers the historical *arr suite scope. See `2026-07-09-refinery-arr-design.md`. Below are the adjacent services that support it or exist alongside.

- **qBittorrent or ruTorrent behind Mullvad VPN** - download client. Container must route all traffic through Mullvad WireGuard tunnel (gluetun sidecar in same podman network namespace). Kill switch: if VPN drops, qBit can't reach internet. Web UI tailnet-only via Traefik. User picks qBit vs ruTorrent at install time. Reusable Mullvad WG module lives in `modules/nixos/shared/mullvad-wg.nix` so Headscale exit node can mount the same.
- **Navidrome successor (custom)** - Subsonic-compatible multi-user music server with fully custom Dead Space themed UI. Replaces `music.ishimura.lol`. Must-haves: Subsonic API compat (so DSub / Substreamer / Symfonium keep working), multi-user (per-user libraries/playlists/history), custom UI matching rec deck / homepage, VoidAuth OIDC. Stack: Flask + music-scanning library + SQLite + Subsonic API endpoint set. Serve raw audio via X-Sendfile / X-Accel-Redirect through Traefik (avoid Flask serving big audio). Absorbs [[fretboard]] as `/instruments` internal path. Own spec doc when work starts.
- **ROMM + EmulatorJS** - ROM library manager + browser emulator. Indexes ROMs from disk via IGDB, pairs with EmulatorJS for play-in-browser. Container both. Consider replacing ROMM with a refinery-integrated view long-term since refinery already has hash + IGDB integration.
- **AudioBookshelf** - audiobooks + podcasts server. Mobile app pairs with the music service for full audio coverage. Container. Point at `/mnt/storage/media/audiobooks`. TBD public vs tailnet.
- **BookLore** already deployed - see [[project_ishimura_normandy_todo]] for OIDC integration status.

## Backup + recovery

- **Automated backup of all non-Nix-managed data to external drive on nostromo** - use restic (preferred, dedupe + encryption + snapshot) or borg. Targets: `/persist` on all 3 hosts (encrypted with sops-managed key), voidauth postgres dumps, Jellyfin metadata, AdGuard config, Grafana SQLite. Schedule: daily incremental, weekly full, monthly archive. Send to ntfy on success/failure. Future: rclone-mirror to cheap S3/B2 for offsite. **See also: [[hangar]] Stage 8 borg-based backup timer + UI - unify with this fleet-wide backup strategy.**
- **Disaster recovery written guide** - step-by-step "bare metal + this guide + sops key + backup snapshot, rebuild the entire stack from zero". Live as `docs/disaster-recovery.md`.
- **Comprehensive security + issue audit** - end-of-roadmap pass. Check every exposed port, Pangolin middleware, container privilege, sops usage, cert renewal, orphaned services, firewall rules. Tune CrowdSec, calibrate Anubis, review Tailscale ACLs. Run lynis on each host.

## Communication + wiki

- **Ishimura Discord server** - user-owned Discord guild for the crew. Real Discord, not self-hosted.
- **Comms Officer Discord bot** - see [[comms officer bot design]] TODO. Bridges ntfy alerts to Discord + slash commands into ishimura services. Full bot spec doc pending.
- **Revolt** (self-hosted Discord alternative) - deploy on normandy, run Discord and Revolt simultaneously, see which sticks. Backlog.
- **Wiki for user help** - candidates: BookStack (clean, single-binary Go, easy theming), Wiki.js (heavier), Outline (Notion-clone, postgres). Mount `wiki.ishimura.lol` public + voidauth-gated for edits.
- **User chat** - IRC vs Matrix debate ongoing. Likely: Matrix (Conduwuit or Synapse) for users + bridge IRC into it for personal use. IRC bouncer (`services.soju`) independent of user-chat decision.
- **Help/FAQ section integrated into homepage** - small static section on ishimura.lol next to GITHUB/ACCOUNT/ADMIN. Content sourced from wiki or Markdown in `dotfiles/config/homepage/help/`.

## Observability (mostly done, Bridge migration pending)

Prometheus + Grafana + Loki + Alloy stack shipped 2026-06-13. See `notes/memory/project_observability_plan.md` for full history. Current state:

- Prometheus on ishimura port 9090, 30d retention, scrapes CrowdSec + Traefik + node_exporter on all 3 hosts + ntfy
- Grafana on ishimura port 3001, sops secret_key, classic dashboard storage
- Loki on ishimura port 3100, 30d filesystem retention
- Alloy replaces Promtail, ships systemd journal from each host

**Known open items:**

- Loki label endpoint hangs in Grafana Explore (infinite spinner). Diagnose Alloy shipping + label cardinality.
- Delete wrong CrowdSec dashboards, find current 1.7.x version from grafana.com
- Grafana theming limited by OSS edition (login page, top nav = enterprise-only). Currently: custom home dashboard, palette overrides via `grafana.ini`, custom favicon.

**Bridge migration:** the "future replacement" discussed in observability notes is now `2026-07-09-bridge-design.md`. Bridge replaces the operator-facing surfaces (Captain's Log, alerts, commands, unit control) while Grafana + Prom + Loki continue as the time-series backend.

## Self-hosted utilities

- **Lightweight cloud storage + temp file uploads**:
  - Persistent per-user file storage with small quota: Filebrowser (single binary, per-user dirs), Seafile (sync clients), Nextcloud (heavy PIM overkill)
  - Anonymous temp upload like 0x0.st or Pomf clone. Ephemeral, smaller scope, separate service
- **Link shortener** - Shlink (nixpkgs) or YOURLS. Tailnet-only admin, public redirects from `s.ishimura.lol`
- **Personal linktree** - simple custom HTML page, no app. Mount on `links.ishimura.lol` via homepage container. LittleLink-style static.
- **Search engine** - SearXNG (`services.searx`) already deployed. Meta-search, escape Google.
- **Home Assistant** - smart home hub. Container recommended. Future expansion if user gets smart-home devices. Nice ntfy integration for door sensors etc.
- **Immich** - self-hosted Google Photos. AI face/object recognition, EXIF, mobile auto-backup. Heavy: API + ML + postgres + redis. `/mnt/storage/media/photos`. Public via Pangolin (mobile app access).
- **Vaultwarden** - Bitwarden-compatible password manager. Lightweight Rust. `services.vaultwarden` nixpkgs. Critical infra: persist `/var/lib/bitwarden_rs/` + backup to nostromo external. Public via Pangolin. Sops for admin token + SMTP creds.
- **It-tools** - dev utilities container. Tailnet-only. Already deployed.
- **Uptime-Kuma** - status page service. User-facing at `status.ishimura.lol`. Grafana covers ops; Kuma is "is X up right now?" for friends. Public, no auth needed.
- **Manyfold** - self-hosted 3D model library manager for STL/STEP/3MF. Rails + postgres + redis. `/mnt/storage/media/3d-models`. Tailnet-only admin.

## Reading + productivity + PKM

- **RSS reader**: FreshRSS vs Miniflux (both nixpkgs). Miniflux lighter, FreshRSS more featureful. Match aesthetic preference. Alternative: fold RSS into `2026-07-08-daily-design.md` daily as its aggregation backend.
- **Bookmarking**: Karakeep (AI tagging, full content archive) vs Linkwarden (polished UI) vs Linkding (minimal fast) vs Readeck (read-later focus). Recommend Karakeep for research, Linkding for clean inbox.
- **Obsidian alternative**: Logseq (outliner) vs Trilium (hierarchical PKM) vs SiYuan (block-based) vs Joplin+Joplin Server (Markdown + E2E mobile) vs AppFlowy (Notion clone FOSS) vs SilverBullet (wiki + executable code blocks). Recommend Logseq if pure-Obsidian feel, Trilium if power features.
- **Recipe manager**: Mealie (clean archive) vs Tandoor (meal planning + shopping lists) vs Grocy (household-everything). Recommend Tandoor if actually planning, Mealie if just library.
- **Wikipedia offline**: Kiwix (ZIM archives via `pkgs.kiwix-tools`). Decision on bundle size: full English (~100GB) vs text-only (~10GB) vs Library-of-Alexandria (~500GB). Mount `wiki-offline.ishimura.lol` tailnet-only.

## Privacy frontends

- **Invidious companion sidecar** - Invidious deployed but video playback errors "Invidious companion is not available." Companion is Deno/TS at github.com/iv-org/invidious-companion. Setup: sops `invidious/companion_key`, podman container `quay.io/invidious/invidious-companion:latest`, env `INVIDIOUS_DOMAIN` + `SERVER_SECRET_KEY`, `invidious_companion` config block, Pangolin route for `/companion`. Same aardvark-dns workaround as pelican-net (AGH holds udp/53).
- **Additional privacy frontends**: Redlib (Reddit), Nitter (Twitter, mostly broken), Whoogle, Libremdb, Anonymous Overflow, Scribe (Medium), Quetre (Quora). All nixpkgs `services.X` modules except libremdb/scribe/quetre/anonoverflow (containers). Same Pangolin + tailnet-only pattern. Aim for one homepage Frontends tile per service.
- **AGH whitelist for YouTube anti-bot scripts** - if friends hit YouTube "sign in to confirm you're not a bot" from home LAN, add `@@||youtube.com^`, `@@||googlevideo.com^`, `@@||ytimg.com^`, `@@||ggpht.com^`, `@@||youtubei.googleapis.com^` to AGH custom rules. Document on homepage admin. May not fully fix if residential IP is also flagged - Invidious-with-companion is the real long-term solution.

## Game servers

Hangar handles KF2, VS, Tarkov-SPT natively - see `2026-07-07-hangar-design.md`. Additional game additions:

- **Additional game modules to add** - Valheim (similar survival to VS), Project Zomboid (survival horror, mod scene like SPT), Mordhau (UE4 medieval melee), Minecraft Paper with `online-mode=false` + AuthMe + SkinsRestorer (offline accounts join), Wolfenstein Enemy Territory (free objective-FPS), Veloren (open-source voxel MMO-lite), Neverwinter Nights EE (classic CRPG persistent worlds), Mindustry (factory tower defense), OpenRA (90s RTS reimplementations), Doom via Zandronum (multiplayer Doom source port - coop, deathmatch, CTF).
- **Standalone always-on containers** (NOT hangar-managed - these want voidauth-gated subdomains + restic backup coverage like Jellyfin):
  - **OpenFrontIO** at `openfront.ishimura.lol` - real-time strategy/territory game, solo vs bots + coop. Build from `github.com/openfrontio/OpenFrontIO`, push to `ghcr.io/cardinal9985/openfront:latest`, pull on normandy. Env: `GAME_ENV=dev`, `DOMAIN`, `NUM_WORKERS=2`, `TURNSTILE_SITE_KEY=1x00000000000000000000AA`, `ADMIN_TOKEN` (sops). nginx on 80, health at `/api/health`. Deploy on normandy (lower latency for multiplayer). Port 4547.
  - **Foundry VTT** at `foundry.ishimura.lol` - if the custom VTT (`2026-07-09-vtt-design.md`) isn't ready, Foundry as interim
  - **2009scape / Lost City** - free OSS old-school RuneScape private servers
  - **TrinityCore / AzerothCore** - WoW Classic/WotLK private server emulators (~6-8GB RAM, postgres backend)
- **Discord game-control bot integration** - part of Comms Officer bot spec. Members `/start <server>` in Discord, bot calls Hangar API to spin up. Bot polls each running server's player count via game query protocol, after N min zero players auto-calls Hangar API to stop. See `2026-07-09-bridge-design.md` for command execution pattern, applies here.

## Auth + registration

- **VoidAuth self-service registration + manual approval + email + custom templates** - user wants visitors hitting `ishimura.lol` to see a Register button on auth page, new accounts go to pending state until approved, all flows send themed emails. Sub-tasks:
  1. Enable self-service signup in voidauth admin UI OR add `SIGNUP_ENABLED=true` (verify exact env var name)
  2. Group-based approval pattern: create `unapproved` group (no access), set as default group on signup; require `user` group on all ProxyAuth domains; admin moves people to `user` when ready
  3. Post-registration redirect to `ishimura.lol` home
  4. Resend account + domain verification for transactional email. Free tier 3000 emails/mo. DNS records: SPF (TXT), DKIM (CNAME or TXT), DMARC (TXT) at Porkbun. Sender: `noreply@ishimura.lol`
  5. Sops secrets + voidauth env vars for SMTP (`voidauth/smtp_password`, plus plaintext env for host/port/user/from). Verify exact env var naming against voidauth source
  6. Custom email templates matching Ishimura aesthetic. Mount custom templates dir via volume like custom.css + logo.svg. Test each template by triggering the flow (register test, password reset, etc)
- **Replace voidauth "authadmin" with "admins"** - voidauth ships non-removable default `authadmin` group. Ensure `admins` is the gate for everything, leave `authadmin` cosmetic. Audit ProxyAuth Domains. Final group set: `admins`, `users`, `unapproved`.
- **Gate Pangolin admin behind voidauth forward-auth** - currently `pangolin.ishimura.lol` is tailnet-only IPAllowList. Add voidauth-forwardauth so even on tailnet only signed-in admins reach it.

## Small quality-of-life fixes

- **Fix VoidAuth status indicator on ishimura homepage** - tile shows red because `no-cors` fetch to `https://auth.ishimura.lol` fails (probably redirect to `/login`). Add `statusPath`/`healthUrl` pair pointing at known-200 endpoint (voidauth `/health` if it exposes one)
- **Homepage migration to Normandy: keep `/admin/` behind VoidAuth forward-auth** - post-migration, replace `allow 100.64.0.0/10; deny all;` with Traefik forwardAuth middleware pointing at VoidAuth `/auth` endpoint, applied only to `PathPrefix(/admin)` router. **Actually this is already covered in `2026-07-09-bridge-design.md` since Bridge absorbs the admin surface**.
- **Local DNS + adblock split-DNS for `*.ishimura.lol`** - AdGuard already deployed. Register as Tailscale "Restricted Nameserver" for `ishimura.lol` so it doesn't override MagicDNS. This unblocks tailnet admin subdomains (tdarr.ishimura.lol etc.) that currently reject because public DNS sends via normandy public IP
- **NFS performance tweaks for Tdarr cluster** - two small gains available on `modules/nixos/nostromo/nfs.nix` automount: (a) `async` so NFS writes return immediately (~20-40% on write-bound work; risk: in-flight writes lost on ishimura crash, acceptable for transcode cache), (b) `nconnect=4` to split across 4 TCP connections (~10-20% gain on gigabit). Defer until disk3 in mergerfs
- **Replace JellyfinSecurity with 9p4/jellyfin-plugin-sso** - JellyfinSecurity hits `DbUpdateConcurrencyException` race in `OidcService.FinalizeSignInAsync` on auto-created OIDC users. Manual workaround: change new user's Auth Provider to "Two-Factor Authentication" in Jellyfin Users admin. Brittle. Plan: install 9p4 plugin, configure same voidauth client with new redirect URI, update voidauth client config, swap login button + CSS rules to target new plugin's button id, uninstall JellyfinSecurity, migrate existing OIDC users
- **Jellyfin login page nested-frame layout polish** - three nested visual frames on login page (form/cyan tint, TV/EMBEDDED yellow inner frame, PRIMARY ACCESS cyan inner frame). Iterated 2026-06-13, paused. Root cause: CSS-only approach doesn't have real wrapper elements. Options: per-child selectors + zero margins, `display: grid` with row backgrounds, `display: contents` + pseudo-element, or fork JellyfinSecurity to inject real wrapper divs. Working file `/tmp/jellyfin-custom.css`, eventually move to `config/jellyfin/custom.css`

## Cross-service profile pictures

- **Voidauth profile picture sync across services** - voidauth exposes avatars via OIDC `picture` claim + LDAP `jpegPhoto`. After upload in voidauth account page, configure each downstream to pull: Jellyfin (LDAP plugin: enable image sync + `LDAP profile image attribute=jpegPhoto`; 9p4 SSO: `Set Avatar URL Format={picture}`), Immich (OIDC picture claim, auto), Nextcloud (OIDC + LDAP), Gitea/Forgejo (OIDC). Confirm each on first deploy. No central push mechanism - each service pulls on login/refresh.

## Dicebear avatar foundry

- **Switch customizer from URL-param HTTP API to client-side JS library** - current `avatars.ishimura.lol` uses dicebear/api:4 with URL query params, restricting to cross-style options only (background, radius, rotate, flip, scale). Per-style customization (bottts mouth/eyes, avataaars hair/clothes) needs @dicebear/core + @dicebear/collection JS library client-side. Plan: nix derivation with `buildNpmPackage` bundling core+collection via esbuild into `bundle.js`. Self-host bundle (~150KB). Rewrite index.html to render dynamic controls per style based on each style's schema. 30+ styles fully customizable. Defers self-hosting purity but Nix-built so reproducible.
- **Auto-set avatar on signup** - hook voidauth signup flow to call voidauth user API + upload generated SVG. Requires voidauth's user API + auth token for service calls. Could also use LDAP jpegPhoto attribute.
- **Inject "Customize Avatar" button on voidauth user page** - Traefik rewriteBody middleware injects `<script>` using MutationObserver to detect user profile page and insert themed button linking to `avatars.ishimura.lol`. Voidauth is Angular SPA so client-side detection needed. Confirm CSP allows it.

## Theming + cleanup

- **Comprehensive theming pass across all services** - extend Dead Space aesthetic everywhere. Custom Jellyfin theme to fully match (currently only login page themed, post-login uses Abyss). Match Grafana palette. Match arr-successor Refinery UI. Match media services as they land.
- **Em-dash + AI-tell sweep across repo** - scan for `—`, ratify against `feedback_no_emdashes` memory. Remove AI tells: excessive comments, "let me" / "I'll" in comments, over-explanatory wording, unnecessary section dividers. Terse and confident.
- **Nix topology diagram + custom network map** - generate visual architecture diagram. nix-topology package exists (renders hosts + services + sops as graph). Pair with hand-drawn Ishimura-aesthetic map showing tailnet IPs, public IP, NFS share, Pangolin tunnel. Hang both on wiki + homepage admin section.

## Custom services (older prototypes)

- **Wrapped** - Jellyfin Wrapped (per-user playback stats end-of-year summary). Source in `config/wrapped/` (Flask + apscheduler poller + pymysql + sqlite for Navidrome). Scaffolding TODO: write `wrapped.nix` similar to `requests.nix`, wire BookLore + ROMM MariaDB credentials (different sops paths), Jellyfin API key, Navidrome sqlite path mounted read-only, update poller `host.containers.internal` URLs to tailnet IPs, add `/health` route. Voidauth-gated at `wrapped.ishimura.lol`, public-with-auth so users see own stats. Actually this is largely covered by `2026-07-09-stats-extension-design.md` - Wrapped becomes a specific rendering of stats' aggregated data. Fold in.
- **Mods** - current mods-server (busybox) exposes `/mods/*` on ishimura.lol for public mod downloads. Rebuild as proper container with per-game structure and add Tarkov mod support alongside existing Skyrim/FNV mods (nostromo has SPT + Fika, friends need matching client mods). Integrate with mo2installer flow on nostromo. Could fold into hangar's mods panel (`2026-07-07-hangar-design.md` Stages 9-10).

## Homelab lab (isolated network)

Small pen-testing lab in an isolated 10.10.10.0/24 network on nostromo.

- **Done**: `lab-scan` (nmap sweep of isolated network to find Metasploitable2 IP without needing virsh console)
- **Future**:
  - Metasploitable3 (Windows 2012 + Ubuntu 1404, Vagrant/Packer setup)
  - Sliver C2 (persistent server container for multi-day engagements) - Exegol already has msfconsole; don't need Sliver until real multi-day engagements
  - VulnHub / Proving Grounds machines (add to `vms/lab.nix` as needed)
  - Local registry mirror (cache lab images so rebuilds don't re-download)
- **Keep it lean** - add VMs/containers lazily, only when actually needed

## Deployment order (rough)

Once dependencies + prep are in:

1. **Bridge** - unblocks fleet-wide ops surface, gates admin properly, absorbs current homepage `/admin`
2. **Refinery arr expansion** - unblocks the media pipeline for everything below
3. **Stats extension** (profiles + achievements + taste profile) - unblocks discover in requests + Now Playing widgets
4. **Daily newspaper** - unblocks the "read the world" habit + release calendar + alerts
5. **Voidauth registration + email + templates** - unblocks friend onboarding without manual work
6. **Comms Officer Discord bot** - unblocks cross-post loops
7. **Backup infrastructure** - unblocks confident iteration on everything else
8. **Navidrome successor** (custom music) + fold in fretboard - reduces third-party service count
9. **Media services (Vaultwarden, Immich, AudioBookshelf)** as user demand emerges
10. **Games hub tile expansion** - opportunistic per-tile
11. **VTT** - only after games hub is ~80%
12. **Nice-to-haves** (RSS reader, bookmarks, PKM, recipe manager, Kiwix) as user picks preferred flavor

## Ties into

- Every other spec doc in `notes/specs/` - this is the meta-roadmap that gives context to per-service work
