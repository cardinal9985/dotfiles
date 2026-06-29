# Client setup (friends joining the server)

Guide for friends connecting to my SPT + Fika server. You're not hosting anything; you just need a local SPT install + Fika.Core that talks to my server over the internet.

## What you need

- A legitimate paid copy of Escape from Tarkov (one-time purchase, you keep the files)
- SPT 4.0.13 installed locally (matches my server version)
- Matching client mods (I'll send you the archives)
- Internet (no Tailscale needed; you connect to a public domain)

## Linux (NixOS) path

### 1. Get the dotfiles bits

In your NixOS config, you need these home-manager packages:

```nix
home.packages = with pkgs; [
  lutris winetricks protontricks umu-launcher
  # plus whatever else
];
```

In your steam config, `programs.steam.extraCompatPackages = [ pkgs.proton-ge-bin ];`.

Optional but recommended: copy `modules/home/maxwell/nostromo/spt.nix` from my dotfiles, change paths to wherever you install SPT, change SPT.Launcher's server URL via the launcher UI (it stores per-user).

### 2. Install Lutris's wine-GE-8-26 runner

Open Lutris > Preferences > Runners > Wine > install `lutris-GE-Proton` or `wine-ge-8-26-x86_64`. Needed for the BSG installer (Proton's wow64 breaks the 32-bit installer).

### 3. Initialize wine prefix

```bash
mkdir -p ~/games/spt
export PROTONPATH=$(nix-build '<nixpkgs>' -A proton-ge-bin.steamcompattool --no-out-link)
export WINEPREFIX=~/games/spt
export GAMEID=umu-default
unset LD_PRELOAD
umu-run wineboot --init
umu-run winetricks -q dotnet48 vcrun2022
```

dotnet48 takes ~10 min and pops Microsoft installer dialogs. Click through.

### 4. Install BSG Launcher

Download BSG Launcher EXE from Battlestate Games' site (need to log in to your account).

Run via wine-ge (NOT Proton - 32-bit installer crashes on Proton 10):

```bash
WINEPREFIX=~/games/spt/pfx \
WINE=~/.local/share/lutris/runners/wine/wine-ge-8-26-x86_64/bin/wine \
steam-run env -u LD_PRELOAD wine ~/path/to/BsgLauncher.X.X.X.exe
```

Keep default install path `C:\Battlestate Games\BsgLauncher`.

### 5. Download EFT (~80GB)

Run the installed BSG launcher via umu/Proton:

```bash
PROTONPATH=$(nix-build '<nixpkgs>' -A proton-ge-bin.steamcompattool --no-out-link) \
WINEPREFIX=~/games/spt GAMEID=umu-default PROTON_VERB=waitforexitandrun \
umu-run "~/games/spt/pfx/drive_c/Battlestate Games/BsgLauncher/BsgLauncher.exe" \
  --disable-software-rasterizer
```

Log in, start the EFT download. Walk away for a while.

### 6. Install SPT 4.0.13

Download the SPT installer from <https://forge.sp-tarkov.com/installer>. Run via Proton:

```bash
umu-run ~/path/to/SPTInstaller.exe
```

Pre-checks will flag missing .NET 9 + ASP.NET Core 9. The installer downloads them but doesn't auto-install. Manually:

```bash
umu-run ~/desktop/windowsdesktop-runtime-9.0.X-win-x64.exe /install /quiet /norestart
umu-run ~/desktop/aspnetcore-runtime-9.0.X-win-x64.exe /install /quiet /norestart
```

Re-run SPT installer. **Set install path to X: drive** (e.g. `X:\games\spt`). Maps to `/home/<user>/games/spt/`. Don't use Z: (sandbox sees only ~30GB free).

### 7. Install Fika.Core + the other client mods

Get the mod archive bundle from me (I'll send a zip via [whatever channel]). Or download individually from <https://forge.sp-tarkov.com>:

| Mod | Required? |
|---|---|
| Fika.Release.2.3.3 | **YES** - co-op client |
| AmandsGraphics 1.6.5 | strongly recommended |
| DrakiaXYZ-BigBrain 1.4.0 | required for SAIN |
| DrakiaXYZ-Waypoints 1.8.2 | required for SAIN |
| SAIN 4.4.3 | strongly recommended (smart AI) |
| Fontaine-FOV-Fix 4.0.1 | recommended (max FOV slider) |
| HollywoodFx 1.8.4 | optional (visuals) |
| Tyfon-UIFixes 5.3.9 | recommended (UI quality of life) |

Extract everything to SPT root (the directory containing `EscapeFromTarkov.exe` after the SPT installer ran):

```bash
SPT_ROOT=~/games/spt  # or wherever
for archive in ~/mods/*.{zip,7z}; do
  case "$archive" in
    *.zip) unzip -o -q "$archive" -d "$SPT_ROOT" ;;
    *.7z)  7z x -y -bd -bso0 "$archive" -o"$SPT_ROOT" ;;
  esac
done
```

If any mod extracted to `~/games/spt/user/mods/` (old SPT 3.x convention), move it to `~/games/spt/SPT/user/mods/`:

```bash
mv "$SPT_ROOT/user/mods/"* "$SPT_ROOT/SPT/user/mods/" 2>/dev/null
rmdir "$SPT_ROOT/user" 2>/dev/null
```

### 8. Launch SPT.Launcher

The critical env var is `WINEDLLOVERRIDES="winhttp=n,b"` - forces wine to load BepInEx's local winhttp.dll instead of wine's built-in. Without it BepInEx doesn't hook, mods don't load, Fika UI doesn't appear.

If you copied my `spt.nix` module, `tarkov` handles this. Otherwise wrap manually:

```bash
PROTONPATH=$(nix-build '<nixpkgs>' -A proton-ge-bin.steamcompattool --no-out-link) \
WINEPREFIX=~/games/spt \
GAMEID=umu-default \
PROTON_VERB=waitforexitandrun \
WINEDLLOVERRIDES="winhttp=n,b" \
umu-run ~/games/spt/SPT/SPT.Launcher.exe
```

In the launcher:
- **Server URL**: `https://games.ishimura.lol:6969`
- Accept the self-signed certificate warning if it appears
- Create a profile (your own - separate from mine)
- Pick an edition (Standard/EOD/Unheard)
- Click Play

### 9. Join my Fika session

After EFT loads to the main menu, look for the Fika panel (usually right side or as a separate tab). Browse / Join. Pick my hosted session.

## Windows path

Largely the same but no wine/Proton wrapping:

1. Install BSG Launcher normally (just run the EXE). Log in, download EFT.
2. Download SPT installer from <https://forge.sp-tarkov.com/installer>. Run it, set install path, let it copy + patch.
3. Install .NET 9 Desktop Runtime + ASP.NET Core 9 from Microsoft if SPT installer flags them. Standard installers.
4. Drop the mod archives into SPT root and extract. Same archives as Linux path.
5. Run `SPT.Launcher.exe` from the install directory.
6. Set server URL to `https://games.ishimura.lol:6969`, accept cert warning.
7. Create profile, click Play, find Fika host in main menu.

No WINEDLLOVERRIDES needed because Windows loads DLLs natively.

## Troubleshooting

If SPT.Launcher won't connect:

- Verify my server is up. From your machine: `curl -kv https://games.ishimura.lol:6969/launcher/server/version` (use `curl.exe` in PowerShell to bypass the alias). Should return 200.
- If timeout: my home router or server is offline, or my IP changed. Message me.
- If "certificate verify failed": you didn't accept the self-signed cert. Try the launcher again.

If Fika UI doesn't appear in EFT main menu:

- Check `<spt-root>/BepInEx/LogOutput.log`. Look for `Loading [Fika.Core 2.3.3]`. If missing, Fika.Core.dll didn't load - check it's at `BepInEx/plugins/Fika/Fika.Core.dll`.
- On Linux, missing `WINEDLLOVERRIDES="winhttp=n,b"` is the most likely cause - BepInEx never initialized.

If the game crashes during raid loading:

- SPT version mismatch with my server. Mine is **4.0.13**. Verify yours via `cat <spt-root>/SPT/SPT_Data/configs/core.json | grep compatibleTarkovVersion` - should show `0.16.9.40087`.
- Mod version mismatch. Make sure you used the exact archives I sent.

For anything else, see [troubleshooting.md](./troubleshooting.md) or message me.
