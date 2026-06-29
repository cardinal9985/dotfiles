# Host setup (Maxwell, on nostromo)

End-to-end guide to replicate this SPT + Fika host setup. Useful if you reinstall nostromo, migrate to a new machine, or want to remember exactly what you did when something breaks.

The setup has three layers and you can do them in roughly this order:
1. **Game install** (wine prefix, EFT, SPT, mods) - manual, ~2 hours including download
2. **Pelican server** (egg import, allocations, container) - ~30 min
3. **Public network exposure** (DNS, port forward, firewall) - ~15 min

## Prerequisites

- NixOS on nostromo with home-manager
- Own a legitimate EFT account (you need BSG credentials to download the game)
- Pelican Panel + Wings already running (yours is on ishimura panel, nostromo wings)
- Pangolin + traefik already running on normandy with domain `ishimura.lol`
- ~100GB free disk space on nostromo

## Phase 1: Game install

### 1.1 Verify NixOS deps are present

Should already be in `modules/home/maxwell/nostromo/gaming.nix`:

```nix
home.packages = with pkgs; [
  lutris winetricks protontricks umu-launcher
  # ... other gaming stuff
];
```

And in steam.nix, `proton-ge-bin` should be in `extraCompatPackages`.

Rebuild if anything's missing:

```
rebuild
```

### 1.2 Install Lutris's wine-GE-8-26 runner

Open Lutris UI > Preferences > Runners > Wine > install `lutris-GE-Proton` (or `wine-ge-8-26`). This downloads to `~/.local/share/lutris/runners/wine/`.

**Why wine-GE-8-26 specifically:** The BSG launcher installer is a 32-bit NSIS app that crashes on Proton 10's "new wow64" thunking layer with `EXCEPTION_ACCESS_VIOLATION` at `0x7bf4bf06`. Wine 8.0 (which wine-ge-8.26 ships) uses the older split-wineserver wow64 and runs the installer fine.

### 1.3 Create the wine prefix shell

Prefix path lives at `/home/maxwell/games/lutris/escape-from-tarkov/`. Two-layer structure:
- `escape-from-tarkov/` - Proton's prefix root (Proton wraps wine in a subdir)
- `escape-from-tarkov/pfx/` - the actual wine prefix that Proton manages
- `escape-from-tarkov/spt/` - SPT install, separate from the wine prefix

Init the Proton prefix and install .NET 4.8 + VC++ 2022 runtimes via umu's winetricks integration. The init script:

```bash
#!/usr/bin/env bash
set -euo pipefail
unset LD_PRELOAD

export PROTONPATH=$(nix-store --query --references $(nix-instantiate '<nixpkgs>' -A proton-ge-bin) | grep steamcompattool | head -1)
export WINEPREFIX=/home/maxwell/games/lutris/escape-from-tarkov
export GAMEID=umu-default
export PROTON_VERB=run

mkdir -p "$WINEPREFIX"
umu-run wineboot --init
umu-run winetricks -q dotnet48 vcrun2022
```

`dotnet48` installer takes ~5-10 min and pops Microsoft installer GUIs. Click through them. If wine asks to "reboot", say yes.

### 1.4 Install BSG Launcher (HYBRID: wine-ge, not Proton)

Download the BSG Launcher installer EXE from Battlestate Games (you need a real account login - the installer fetches your purchased EFT).

Run via wine-ge (NOT Proton/umu) into the Proton-initialized prefix's `pfx/` subdir:

```bash
WINEPREFIX=/home/maxwell/games/lutris/escape-from-tarkov/pfx \
WINE=/home/maxwell/.local/share/lutris/runners/wine/wine-ge-8-26-x86_64/bin/wine \
steam-run env -u LD_PRELOAD wine ~/desktop/BsgLauncher.X.X.X.exe
```

**Why hybrid:** Proton 10's wow64 thunking breaks the 32-bit BSG installer (see 1.2). But wine-ge can write into a Proton-initialized prefix because wine prefix internals (drive_c, registry) are mostly compatible across wine versions. After install, BsgLauncher.exe (64-bit binary) runs fine under Proton.

Install path: keep default `C:\Battlestate Games\BsgLauncher` (maps to `pfx/drive_c/Battlestate Games/BsgLauncher/`).

### 1.5 Download EFT

Launch BSG Launcher via Proton:

```bash
PROTONPATH=<proton-ge-bin path> WINEPREFIX=... GAMEID=umu-default \
umu-run "/home/maxwell/games/lutris/escape-from-tarkov/pfx/drive_c/Battlestate Games/BsgLauncher/BsgLauncher.exe" \
  --disable-software-rasterizer
```

Log in, start EFT download. ~80GB. Walk away.

When done, EFT lives at `pfx/drive_c/Battlestate Games/Escape from Tarkov/`.

### 1.6 Install SPT

Download SPT Installer (.exe) from <https://forge.sp-tarkov.com/installer>. Run via Proton:

```bash
umu-run ~/desktop/SPTInstaller.exe
```

Pre-checks will flag missing .NET 9 Desktop Runtime + ASP.NET Core 9 Runtime. The installer downloads the official Microsoft installers to your desktop but doesn't auto-install. Run them yourself:

```bash
umu-run ~/desktop/windowsdesktop-runtime-9.0.X-win-x64.exe /install /quiet /norestart
umu-run ~/desktop/aspnetcore-runtime-9.0.X-win-x64.exe /install /quiet /norestart
```

Re-run the SPT installer. Set install path to `X:\games\lutris\escape-from-tarkov\spt` (X: maps to /home/maxwell, so this lands at `~/games/lutris/escape-from-tarkov/spt/` - a sibling of `pfx/`, not inside the wine prefix).

**Don't use Z: drive:** Z: maps to `/` (linux root). Pressure-vessel sandbox reports only ~30GB free on Z: even when /home has hundreds of GB - the installer's free-space check fails. X: bypasses this.

SPT installer copies EFT files to the new SPT directory and patches them. ~10-15 min for 80GB of files.

### 1.7 Fix native Linux server executable bit

SPT 4.x ships a native Linux server binary alongside the Windows one. The installer ran via wine, so it doesn't preserve the unix exec bit:

```bash
chmod +x /home/maxwell/games/lutris/escape-from-tarkov/spt/SPT/SPT.Server.Linux
```

Without this you get "Permission denied" trying to run it natively.

### 1.8 Install mods

Mods extract directly to SPT root (`spt/`). Modern SPT mod archives put `BepInEx/` and `SPT/user/mods/` at archive root, so extraction lays them down in the right place.

Required archives (download from <https://forge.sp-tarkov.com>):

| Mod | Type | Notes |
|---|---|---|
| Fika.Release.2.3.3.zip | Client + Server | Co-op framework. Client only at this version - server bits installed via Pelican egg toggle. |
| Project Fika - Server | Server | Server-side companion for Fika 2.3.3. Without this Fika UI doesn't show on main menu. |
| AmandsGraphics.1.6.5.zip | Client | Visual enhancement |
| Fontaine-FOV-Fix-v4.0.1-SPT-v4.x.x.zip | Client | Expanded FOV slider |
| HollywoodFx_1.8.4.7z | Client | Visual effects |
| Tyfon-UIFixes-5.3.9.zip | Client + Server | UI quality-of-life |
| SVM.Server.Value.Modifier.zip | Server | Tweaks XP/loot/prices. Disabled until configured via Greed.exe |
| DrakiaXYZ-BigBrain-1.4.0.7z | Client | Bot AI library; SAIN dependency |
| DrakiaXYZ-Waypoints-1.8.2.7z | Client | Bot pathing; SAIN dependency |
| SAIN.4.4.3.zip | Client + Server | Smart AI overhaul |

Don't install:
- `Corter-ModSync-v0.11.1.zip` - SPT 3.x only, dead project, doesn't work on 4.x

Bulk extract:

```bash
SPT_ROOT=/home/maxwell/games/lutris/escape-from-tarkov/spt
for archive in ~/desktop/mods/*.{zip,7z}; do
  case "$archive" in
    *.zip) unzip -o -q "$archive" -d "$SPT_ROOT" ;;
    *.7z)  7z x -y -bd -bso0 "$archive" -o"$SPT_ROOT" ;;
  esac
done
```

Some mods use OLD SPT 3.x path conventions (`user/mods/`) instead of 4.x (`SPT/user/mods/`). Manually move any 3.x-convention mods:

```bash
mv "$SPT_ROOT/user/mods/"* "$SPT_ROOT/SPT/user/mods/" 2>/dev/null || true
rmdir "$SPT_ROOT/user" 2>/dev/null || true
```

### 1.9 Apply WINEDLLOVERRIDES for BepInEx

EFT under Proton needs wine to load the local `winhttp.dll` (BepInEx's doorstop hook) instead of wine's built-in. Without this, BepInEx never initializes and all your client mods (incl. Fika) don't load.

The `tarkov` wrapper in `spt.nix` sets `WINEDLLOVERRIDES="winhttp=n,b"` automatically. If you're launching manually, set that env var. To verify it took:

```bash
ls ~/games/lutris/escape-from-tarkov/spt/BepInEx/LogOutput.log
# After a successful launch, file exists and contains "Chainloader startup complete"
```

### 1.10 The wrappers

Once installed, `modules/home/maxwell/nostromo/spt.nix` provides:

- `tarkov` - launches SPT.Launcher.exe via Proton + umu + WINEDLLOVERRIDES
- `tarkov-svm` - launches SVM's Greed.exe config editor
- `tarkov-server` - runs SPT.Server.Linux natively (no wine) - for offline play; conflicts with Pelican if both run

Desktop entries auto-register, so "SPT Tarkov" shows in rofi.

Add `tarkov` as a Non-Steam Game in Steam: Add a Non-Steam Game > Browse to `/etc/profiles/per-user/maxwell/bin/tarkov`. **Disable Steam's compat tool** on this entry (Properties > Compatibility > uncheck "Force the use of a specific Steam Play compatibility tool"). Our script handles Proton itself; double-wrapping breaks it.

## Phase 2: Pelican server

For Fika co-op you need a persistent SPT server. We use Pelican to manage it as a container on nostromo.

### 2.1 Import the egg

Use Shardbyte's egg: <https://github.com/Shardbyte/shard-egg-basket/blob/main/games/eft/egg-eft-fika.yaml>

In Pelican panel: Admin > Eggs > Import > paste the YAML.

**Why Shardbyte:** Linux-native (no wine yolk), builds SPT from source via `dotnet publish`, debian-based, transparent build process. Targets SPT 4.0.x. Has Fika toggle.

### 2.2 Create allocations on nostromo node

Admin > Nodes > nostromo > Allocations. Add these on nostromo's LAN IP (NOT tailnet IP):

- `192.168.254.95:6969/TCP` - SPT.Server HTTP/WebSocket
- `192.168.254.95:6790/UDP` - Fika game traffic

**Why LAN IP not tailnet IP:** Pelican binds Docker container ports to the allocation IP exactly. We want external port-forward to work, so Wings binds 6969 on the LAN interface where the home router can deliver forwarded packets.

### 2.3 Create the server

Admin > Servers > new server:
- Owner: maxwell
- Node: nostromo
- Primary allocation: `192.168.254.95:6969` (TCP)
- Additional: `192.168.254.95:6790` (UDP)
- Resources: 0 CPU/memory (unlimited), 20480 MiB disk, OOM Killer enabled, Backups 5
- Egg: SPT Fika (just imported)
- Egg variables: `SPT_VERSION=4.0.13`, `SPT_FIKA=1`

Create. First boot builds SPT from source via dotnet (~5-10 min on nostromo's 7600X).

### 2.4 Upload server mods to Pelican

Your local SPT/user/mods/ has server-side mods (Solarint-SAIN-ServerMod, SVM, Tyfon UIFixes Server). The Pelican-built server only has Fika.Server. Upload the others.

Via Pelican panel File Manager:
- Navigate to `/home/container/SPT/user/mods/`
- Drag-drop the mod folders OR upload zips and unzip via the panel

Via SFTP (if Wings has SFTP enabled):
- Pelican panel > server settings shows SFTP credentials
- `rsync -av ~/games/lutris/escape-from-tarkov/spt/SPT/user/mods/Solarint-SAIN-ServerMod sftp://maxwell@nostromo:port//home/container/SPT/user/mods/` (adjust)

Restart the server. Log should show:
```
ModLoader: loading: N server mods...
Mod: SVM ... loaded
Mod: SAIN ... loaded
...
```

### 2.5 Configure SVM via Greed

SVM stays disabled until you configure it. Run `tarkov-svm` (or via rofi: "SPT - SVM Config"). Pick a preset, tweak values, hit Save+Apply. Generates JSON in `[SVM] Server Value Modifier/Loader/` and `Presets/`.

Copy the generated JSON files to the Pelican server's matching path:
- `~/games/lutris/escape-from-tarkov/spt/SPT/user/mods/[SVM] Server Value Modifier/Loader/*.json` → Pelican: `/home/container/SPT/user/mods/[SVM] Server Value Modifier/Loader/`
- Same for `Presets/`

Restart Pelican server. SVM should now load (not say "Initialization cancelled").

## Phase 3: Public network exposure

### 3.1 DNS record

In Porkbun > DNS for `ishimura.lol` > add A record:
- Type: A
- Host: `games`
- Answer: home public IP (current: `47.198.242.37`, check with `curl ifconfig.me`)
- TTL: 600

If your home IP rotates often, switch to DDNS via Porkbun API + a systemd timer on nostromo. For most residential fiber/cable it's stable.

### 3.2 Home router port forward

Forward inbound public ports to nostromo's LAN IP:

| Public | → | Nostromo LAN |
|---|---|---|
| 6969/TCP | → | 192.168.254.95:6969 |
| 6790/UDP | → | 192.168.254.95:6790 |
| 42420/UDP | → | 192.168.254.95:42420 (Vintage Story, optional) |

**Set a DHCP reservation** for nostromo's MAC `30:56:0f:24:b0:b7` (permanent MAC) so the LAN IP doesn't rotate. If NetworkManager's MAC randomization is on (current default), nostromo's active MAC is random per reconnect - add `networking.networkmanager.ethernet.macAddress = "permanent"` to nostromo's network.nix to pin it to permanent if reservation breaks.

### 3.3 Open firewall

`modules/nixos/nostromo/network.nix` already has these. If you're starting fresh, the relevant config:

```nix
firewall = {
  enable = true;
  allowedTCPPorts = [
    36475  # SSH
    6969   # SPT.Server
  ];
  allowedUDPPorts = [
    6790   # Fika
    42420  # Vintage Story (if exposing)
  ];
};
```

### 3.4 Verify external reach

From your phone on cellular (off WiFi) or have someone outside the LAN test:

```
curl -k https://games.ishimura.lol:6969/launcher/server/version
```

Expected: HTTP 200 with compressed body. Anything else means a step above is wrong.

## Daily flow

After setup, day-to-day:

- Start SPT server: it's auto-running on Pelican; check status at <https://pelican.ishimura.lol> if needed
- Launch game: `tarkov` from terminal, rofi, or Steam non-Steam shortcut
- In SPT.Launcher: Server URL `https://games.ishimura.lol:6969`, log in to your profile, click Play
- Friend connects via Fika UI in main menu after they launch their client

## Bringing the local server up (for offline tests)

If Pelican is down or you're offline, you can run SPT.Server.Linux locally:

```bash
tarkov-server
```

Then point SPT.Launcher at `https://127.0.0.1:6969` for the duration. **Stop the Pelican container first** or you'll get a port conflict.

## Where things are

| What | Where |
|---|---|
| Wine prefix | `~/games/lutris/escape-from-tarkov/pfx/` |
| Patched EFT files | `~/games/lutris/escape-from-tarkov/spt/` |
| SPT server + mods (local) | `~/games/lutris/escape-from-tarkov/spt/SPT/` |
| BepInEx client plugins | `~/games/lutris/escape-from-tarkov/spt/BepInEx/plugins/` |
| BepInEx log (for crashes) | `~/games/lutris/escape-from-tarkov/spt/BepInEx/LogOutput.log` |
| Pelican container files | `/var/lib/pelican/volumes/<uuid>/` on nostromo |
| Wrappers / desktop entries | `modules/home/maxwell/nostromo/spt.nix` |
| Mod archives backup | `~/desktop/mods/!Extracted/` |

## See also

- [client.md](./client.md) - friend setup
- [troubleshooting.md](./troubleshooting.md) - symptom-keyed reference
