# SPT troubleshooting

Symptom-keyed reference. Search for the error you're seeing.

## BSG Launcher installer crashes immediately

**Symptom:** Run BSG launcher installer EXE via umu/Proton, process exits in ~5 seconds without any UI. Proton log shows:
```
err:seh:NtRaiseException Unhandled exception code c0000005 flags 0 addr 0x7bf4bf06
```

**Cause:** BSG installer is a 32-bit NSIS bootstrap. Proton 10.x uses "new wow64" thunking that's incompatible with this installer - it crashes inside ntdll's startup hooks.

**Fix:** Install via wine-GE-8-26 (wine 8.0 base) instead of Proton. Wine 8.0 uses the old split-wineserver wow64. The installed BsgLauncher.exe is 64-bit and runs fine under Proton at runtime - the wow64 issue is only the installer.

## SPT.Launcher opens but doesn't connect to server

**Symptom:** Launcher UI opens, log in works, but Play does nothing or EFT crashes immediately.

**Cause:** BepInEx isn't hooking into Unity, so SPT client patches don't apply. EFT tries to talk to BSG's online servers and fails.

**Diagnostic:** Check `<spt-root>/BepInEx/LogOutput.log`. If empty or missing → BepInEx didn't run. If present with `Chainloader startup complete` → BepInEx loaded.

**Fix:** Set `WINEDLLOVERRIDES="winhttp=n,b"` in the launch environment. Wine needs to prefer the local `winhttp.dll` (BepInEx's doorstop) over its built-in. The `tarkov` wrapper does this; if launching manually, prepend it.

## "Permission denied" running SPT.Server.Linux

**Symptom:**
```
$ ./SPT.Server.Linux
bash: ./SPT.Server.Linux: Permission denied
```

**Cause:** SPT installer ran via wine, which doesn't preserve unix execute bits on extracted files.

**Fix:** `chmod +x <spt-root>/SPT/SPT.Server.Linux`. Same may apply if you ever re-extract SPT archives.

## SPT.Server.Linux: "You must install .NET to run this application"

**Symptom:**
```
$ ./SPT.Server.Linux
You must install .NET to run this application.
App host version: 9.0.X
.NET location: Not found
Failed to resolve libhostfxr.so
```

**Cause:** SPT.Server.Linux is framework-dependent .NET, needs runtime on the host system.

**Fix:** Wrap in `steam-run` (for FHS) + set `DOTNET_ROOT`:

```bash
DOTNET_ROOT=$(nix-build '<nixpkgs>' -A dotnet-aspnetcore_9 --no-out-link)/share/dotnet \
  steam-run ./SPT.Server.Linux
```

The `tarkov-server` wrapper handles this automatically.

## SPT.Server starts but immediately stops

**Symptom:** Pelican console (or local terminal) shows server initialization but ends in:
```
THE SERVER HAS UNEXPECTEDLY STOPPED
```

**Diagnostic:** Check `<spt-root>/SPT/user/logs/spt/spt<date>.log`. Last lines reveal where it died.

**Common causes:**
- Missing .NET 9 / ASP.NET Core 9 runtimes inside wine prefix (if running via Proton) - install both via `umu-run windowsdesktop-runtime-9.0.X-win-x64.exe`
- Mod fails to load - the error mentions the mod name
- Port 6969 already in use (local `tarkov-server` + Pelican container at the same time)

## Pelican install script hangs

**Symptom:** Pelican panel shows server installing forever, no progress visible in panel console.

**Diagnostic:** Watch the install container's logs from nostromo:

```bash
sudo docker ps -a | grep installer
sudo docker logs -f <installer-container-id>
```

You'll see dotnet restore + publish output. First install takes ~5-15 min.

**Common stalls:**
- Slow network pulling NuGet packages
- Insufficient disk for dotnet publish (need ~3GB build artifacts)

## Pelican server can't be reached externally (TCP timeout)

**Symptom:** `curl -k https://games.ishimura.lol:6969/...` times out from outside the LAN.

**Diagnostic order:**
1. From nostromo: `curl -k https://192.168.254.95:6969/launcher/server/version` - should return 200. If not, server isn't bound to LAN IP (wrong allocation in Pelican).
2. From nostromo: `ss -tlnp | grep 6969` - should show Wings/Docker listening on `192.168.254.95:6969`.
3. From a phone on cellular: `curl -k https://games.ishimura.lol:6969/...`. If timeout, port forward isn't routing.
4. `dig games.ishimura.lol` - should return your home public IP. If wrong, Porkbun A record is stale.

**Fixes:**
- Wrong allocation: change Pelican allocation from `100.107.103.76:6969` (tailnet) to `192.168.254.95:6969` (LAN), restart server.
- Missing port forward: home router has no rule forwarding `WAN:6969 → 192.168.254.95:6969`.
- Wrong DNS: update Porkbun A record to current public IP (`curl ifconfig.me`).
- Firewall: `modules/nixos/nostromo/network.nix` must allow 6969/TCP.

## Pelican's Pangolin raw resources never reach newt

**Symptom:** You created a TCP/UDP raw resource in Pangolin admin UI, Traefik shows the router in its dynamic config, but external connections hang or RST. Newt log shows `Started tcp proxy to <ip>:<port>` but data doesn't flow. Newt's WG pings time out.

**Cause:** Newt's WireGuard tunnel to Gerbil is broken. Multiple possible reasons:
1. Pangolin can't reach Gerbil's HTTP API at `host.containers.internal:3004` (firewall blocks bridge interface)
2. Newt version mismatch with Pangolin (1.12.4 vs 1.18 broke wg/register protocol)
3. UDP hole-punching fails through home NAT

**Fixes attempted (in our setup):**
- Updated newt to 1.13.0 via overrideAttrs in `modules/nixos/ishimura/newt.nix`
- Added `interfaces.podman1.allowedTCPPorts = [ 3004 ]` to normandy's network.nix
- Removed `tailnet-only` middleware from api-router in normandy's pangolin.nix

Even after all that, WG packets were still unreliable between newt and gerbil. **Final solution: skip Pangolin for game traffic entirely.** Use direct home-router port-forward instead. Game traffic doesn't go through normandy.

## "Tailnet-only" 403 for newt

**Symptom:** Newt's log shows HTML pages with `CEC SECURITY MATRIX` text instead of API responses.

**Cause:** Pangolin's API router has the `tailnet-only` middleware (sourceRange `100.64.0.0/10`). Newt connects via public IP (its source IP isn't in the tailnet range), gets 403.

**Fix:** Either remove `tailnet-only` from api-router (we did this), or pin DNS so newt connects via tailnet:
- Removing tailnet-only: edit `modules/nixos/normandy/pangolin.nix`, drop `tailnet-only` from api-router's middlewares list. Pangolin's API has its own token auth.
- DNS pinning: add `networking.extraHosts = "100.X.X.X pangolin.ishimura.lol";` on the newt host. This causes problems if the WG endpoint goes through Tailscale (double encapsulation → MTU issues).

We chose removing tailnet-only.

## Greed.exe: "couldn't find ServerValueModifier.dll"

**Symptom:** Launch Greed.exe via tarkov-svm, error dialog:
```
Greed couldn't find ServerValueModifier.dll under SPT/user/mods[SVM] Server Value Modifier
Be sure you installed mod correctly, this application (Greed.exe) should be located on same place as game executable
```

**Cause:** Greed uses relative paths and expects its CWD to be the SPT install root (next to `EscapeFromTarkov.exe`). The mod is at `SPT/user/mods/[SVM] Server Value Modifier/` relative from there.

**Fix:** Launch with CWD set to SPT root. The `tarkov-svm` wrapper does `cd ${sptInner}` before exec. If running manually, `cd <spt-root>` first.

## Fika UI doesn't appear in EFT main menu

**Symptom:** All mods load per BepInEx log including `Fika.Core 2.3.3`, but no Fika panel/button in EFT main menu.

**Causes (in order of likelihood):**
1. **Missing Project Fika - Server companion mod** - Fika 2.x client needs server-side counterpart. Check `<spt-root>/SPT/user/mods/` for `fika-server` or similar directory. If absent, download Project Fika - Server from forge and extract.
2. **You're looking in the wrong place** - Fika 2.x for SPT 4.x doesn't add a launcher button. It adds the UI inside EFT's main menu after you log in (right side, or as a separate tab depending on Fika version).
3. **Fika.Core not actually loaded** - grep BepInEx log: `grep "Fika.Core" LogOutput.log`. If missing, doorstop didn't hook (see WINEDLLOVERRIDES section).

## SAIN: "Failed to Import EFT Bot Settings"

**Symptom:** SAIN loads but spams errors for every bot type:
```
[Error :SAIN] Failed to Import EFT Bot Settings for Scav
[Error :SAIN] Failed to Import EFT Bot Settings for Bear
...
```

**Cause:** SAIN reads EFT's vanilla bot settings to layer its own AI on top. The path/file format may have changed in SPT 4.0.13 (SAIN 4.4.3 targets `~4.0.0`).

**Impact:** SAIN's core smart AI still runs - bots will use cover, flank, react to sound. But per-bot tuning falls back to SAIN defaults instead of vanilla-derived values. Bots may behave more uniformly than they should (a Scav might react more like a generic SAIN bot rather than specifically a Scav).

**Fix:** Wait for a SAIN release that explicitly targets your SPT version. Not blocking gameplay.

## SVM: "Initialization cancelled"

**Symptom:** Server log shows:
```
[SVM] Initialization cancelled: Preset or/and Loader is not found or null
Be sure you clicked Save and Apply in Greed.exe
Mod is disabled
```

**Cause:** SVM stays disabled until you configure a preset.

**Fix:** Run `tarkov-svm`, pick a preset (or build your own), hit Save+Apply. JSON files generated under `Loader/` and `Presets/`. If running on Pelican, copy those JSON files to the Pelican server's matching paths.

## ld.so LD_PRELOAD errors during wine/Proton launch

**Symptom:** Lots of:
```
ERROR: ld.so: object '/nix/store/.../gamemode-X.X.X/lib/libgamemodeauto.so' from LD_PRELOAD cannot be preloaded
```

**Cause:** Your shell session has a stale `LD_PRELOAD` env var pointing at a nix-store gamemode lib that's been garbage-collected. The "ignored." at end of each error = ld.so kept going.

**Fix:** Harmless noise. Log out + back in (or reboot) to get a fresh session with the current gamemode path. To suppress: `unset LD_PRELOAD` at the top of your wrapper scripts (`tarkov` already does this).

## EFT crashes with shader/Direct3D errors

**Symptom:** EFT launches briefly then crashes. Player.log shows D3D11 errors or shader compilation failures.

**Cause:** Usually outdated GPU driver, or DXVK issues with EFT's particular shader use.

**Fix:** Update NVIDIA driver via NixOS rebuild. EFT/SPT on Proton-GE 10-34 + recent NVIDIA driver should work cleanly on 30/40-series cards.

## Steam launches `tarkov` script and it dies instantly

**Symptom:** Click Play in Steam on the non-Steam-game shortcut, brief flash, returns to "Play" state.

**Cause:** Steam wrapped the script in Proton anyway despite the checkbox unchecked.

**Fix:** Right-click shortcut > Properties > Compatibility > confirm "Force the use of a specific Steam Play compatibility tool" is **unchecked**. Restart Steam if necessary. Verify the script works standalone first: `tarkov` from a terminal.

## See also

- [host.md](./host.md) - full host setup flow
- [client.md](./client.md) - friend's connection guide
