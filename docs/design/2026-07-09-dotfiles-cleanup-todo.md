# Dotfiles Cleanup + Improvements TODO

**Status:** consolidated from notes/memory/fix.md (2026-06-10 audit) + notes/memory/todo.md (300-item improvement list) on 2026-07-09. Some items may already be resolved - flag as fixed as we go.

**One-liner:** Grab-bag of dotfiles bugs, deprecated patterns, redundancies, and improvement ideas. Not a spec of a service - a running maintenance list. Higher-priority items at the top; sprawling improvement ideas after.

## Duplicate + redundant imports

- **`hosts/nostromo/configuration.nix` lines 4-8** - imports `./hardware-configuration.nix` but `flake.nix` line 103 also imports it directly. NixOS deduplicates, but noise.
- **`modules/nixos/shared/fonts.nix` vs `modules/nixos/nostromo/stylix.nix`** - both configure font packages + fontconfig. Overlap on JetBrains Mono Nerd Font, Inter, Noto Emoji.
- **`modules/home/maxwell/shared/shell.nix` lines 48-50 + `prompt.nix` lines 4-6** - both set `programs.starship.enable = true`. Nix merges without error but could break if one flips.
- **`modules/nixos/nostromo/gpu.nix` line 23** - `nvtopPackages.nvidia` also in `modules/nixos/nostromo/packages.nix` line 16.
- **`modules/nixos/nostromo/audio.nix` line 60** - `usbcore.autosuspend=-1` also in `power.nix` line 23. Keep in power.nix.
- **`modules/nixos/nostromo/boot.nix` line 17** - `kvm-amd` also in `hardware-configuration.nix` line 13 and `virtualisation.nix` line 13. Kernel module loaded 3 times.
- **`virtualisation.nix` line 21** - virt-manager in both systemPackages and `programs.virt-manager`. `programs.virt-manager.enable` already installs it.
- **`desktop.nix` lines 18-22 (system) + `zen.nix` lines 10-15 (user)** - mime types duplicated. User-level wins; system-level is dead code.

## Deprecated / discouraged patterns

- **`modules/nixos/nostromo/nix-settings.nix` lines 12-13** - `keep-outputs = true` and `keep-derivations = true` were removed in Nix 2.20+. Move to garbage-collector options.
- **`modules/nixos/nostromo/nix-settings.nix` line 8** - `auto-optimise-store = true` is discouraged (runs store optimization after every build). Recommended: run `nix store optimise` weekly via timer.
- **`modules/nixos/nostromo/steam.nix` line 18** - `extraProfile` with `LD_PRELOAD` for gamemode is legacy. Use `programs.steam.gamemode.enable = true` instead.
- **`overlays/deskmat.nix` line 4** - `version = "unstable-2025"` should be `"unstable-2026"`.

## Flake + input issues

- **Missing `follows` for impermanence** - `impermanence` input (line 7 of `flake.nix`) doesn't have `inputs.nixpkgs.follows = "nixpkgs"`. Lock file shows `impermanence -> nixpkgs` at different revision (`e4bae1b...`) than root `nixpkgs_3` (`64c08a7...`). Drags in separate stale nixpkgs copy. Fix: add `inputs.nixpkgs.follows = "nixpkgs"`.
- **No flake formatter** - add `formatter = nixpkgs.legacyPackages.x86_64-linux.alejandra;` (or nixpkgs-fmt) to enable `nix fmt`.
- **No flake checks** - no `checks` output for CI or `nix flake check`.
- **No devShell** - add `devShells` for working on the flake.

## Configuration concerns

- **`modules/nixos/nostromo/user.nix` line 17** - `root.hashedPassword = "!"` locks root but is non-standard. `null` (no password) or `"*"` (explicit lock) is standard.
- **`modules/nixos/nostromo/power.nix` lines 4-8** - all sleep/suspend/hibernate targets disabled. If intentional (desktop always on), fine, but companion `hypridle` can never trigger suspend.
- **`modules/nixos/nostromo/ai.nix` lines 11-12** - uses `ollama/ollama:latest` tag. Non-reproducible. Pin specific version.
- **`modules/nixos/nostromo/ai.nix` line 43** - same for `ghcr.io/open-webui/open-webui:main`. Pin specific tag.
- **`modules/home/maxwell/nostromo/awww.nix` line 12** - wallpaper path uses `~` which waypaper reads as literal tilde. Should be `/home/maxwell/dotfiles/wallpapers/fern-1.png` or `config.home.homeDirectory`.
- **`modules/home/maxwell/nostromo/hyprland.nix` line 182** - check if `gpu-screen-recorder -save` subcommand flag is still correct.
- **`security.nix` line 57** - vulnix-scan `notify-send` runs as root in system service, DBUS inaccessible. Hardcoded `DBUS_SESSION_BUS_ADDRESS` is fragile. Use `systemd.user` service instead.
- **`desktop.nix` line 5** - Plasma 6 + Hyprland both enabled pulls in KDE's full session stack alongside Hyprland (display manager, hundreds of packages, file manager). If keeping Plasma, add `xdg-desktop-portal-kde` for proper XDG portal.
- **`gpu.nix` line 22** - nvidia-vaapi-driver installed but unconfigured. Needs `environment.sessionVariables.NVD_BACKEND = "direct"` or similar to enable.
- **`credentials.nix` lines 27-29** - `home.sessionVariables` uses PAM sessions, so `SSH_AUTH_SOCK` may not be available in all contexts (some systemd units).
- **`kitty.nix` line 13** - `hide_window_decorations = false` with Hyprland gives double titlebars.

## Style / maintainability

- **`modules/home/maxwell/nostromo/aliases.nix`** - `secrets` alias includes `sudo` + SOPS key path. Embeds path in shell alias.
- **`modules/nixos/nostromo/steam.nix` line 39** - `apply_gpu_optimisations = "accept-responsibility"` is the actual string gamemode expects to acknowledge GPU OC risks. Add comment.
- **`nixcord.nix`** - 248-line file, mostly plugin config. Consider extracting CSS to separate file.
- **`steam.nix` line 56** - `vm.max_map_count = 2147483642` is one less than `INT_MAX`. Typical gaming recommendation is `2147483642` so probably right, but verify.

## High-priority improvements

1. Add `inputs.nixpkgs.follows = "nixpkgs"` to impermanence input (flake.nix line 7)
2. Replace deprecated `keep-outputs`/`keep-derivations` with newer GC options
3. Remove or timer-ize `auto-optimise-store`: set to `false`, add weekly `nix store optimise` timer
4. Pin container image tags in `ai.nix` instead of `:latest`/`:main`
5. Remove duplicate starship enable from either `shell.nix` or `prompt.nix`

## Medium-priority improvements

6. Deduplicate `usbcore.autosuspend=-1` - keep in `power.nix`, remove from `audio.nix`
7. Clean up triple `kvm-amd` kernel module loading
8. Add flake formatter (alejandra or nixpkgs-fmt)
9. Add devShell for flake work
10. Remove duplicate `hardware-configuration.nix` import from `configuration.nix`
11. Fix `~` in wallpaper path in `awww.nix`
12. Fix `steam.nix` gamemode LD_PRELOAD - use `programs.steam.gamemode.enable = true`

## Low-priority improvements

13. Extract shared config between `fonts.nix` and `stylix.nix` font configs
14. Update deskmat overlay version to 2026
15. Add `nix flake check` compat (empty `checks` output or fix eval warnings)
16. Pre-commit hook / treefmt for code quality
17. Audit `steam.nix` kernel sysctls (`vm.max_map_count`)

## Future improvement ideas (backlog)

Grabbed from the 300-item todo. Rank by curiosity + real payoff.

### Boot / bootloader

- Pre-build snapshot automation: script snapshots `@` before each `nh os switch` for instant rollback
- Secure boot via lanzaboote (already systemd-boot, so signed EFI binaries is natural)
- TPM LUKS auto-unlock via systemd-initrd - removes passphrase prompt at boot
- Boot health check + auto-rollback - systemd service marks success each boot, systemd-boot auto-selects previous generation on 3 failures
- NixOS live ISO from flake via nixos-generate - disaster recovery without external drive

### Package management + updates

- nvd (nix package diff): `programs.nvd.enable = true` pairs with `nh` to show what changed between builds
- Automatic flake update PRs via Renovate or GitHub Actions
- Self-hosted binary cache (attic) on local network
- Low-disk-space GC trigger via `systemd.path` when /nix hits threshold
- nix-output-monitor (`nom`) for real-time build progress
- Per-package unfree instead of global `allowUnfree = true` - use `allowUnfreePredicate` with explicit list

### Backups

- Backups (restic / borg) with impermanence + /persist already in place - see also `2026-07-09-services-roadmap.md` for fleet-wide strategy
- Automatic snapshot sync of `@snapshots` to external disk or S3 - btrfs strategy lacks off-device copies

### Fleet expansion

- `mkHost` is ready - a laptop sharing `shared/` modules is low effort
- nixos-anywhere for provisioning new machines from flake over SSH
- VM test for config changes: `nixos-rebuild build-vm` before deploying to bare metal
- Declarative libvirt VM definitions - currently imperative shell scripts (ZealOS, Whonix, Metasploitable)
- Declarative USB attach for VMs - auto-hotplug Rocksmith / Scarlett via udev when VMs start

### Monitoring / health

- Disk health monitoring - `smartmontools` installed but nothing watches it. systemd user timer + notify-send for SMART errors
- healthchecks.io heartbeat - timer pings for critical services (SSH, ollama, GC, vulnix)
- Impermanence drift detection - service scans for files written outside /persist that aren't in `environment.persistence`, warns before reboot deletion
- NVIDIA dmesg error checking - boot-time or hourly check for Xid errors via notify-send
- RAPL power monitoring - `powercap` readings via Waybar module or systemd timer

### NVIDIA + display

- NVIDIA Wayland hardening env vars: `WLR_NO_HARDWARE_CURSORS`, `__GLX_VENDOR_LIBRARY_NAME`, `GBM_BACKEND`, `AQ_DRM_EXPLICIT_SYNC` for tear-free
- Per-game Hyprland window rules - force fullscreen, disable borders, pin specific games to workspaces (e.g. `noborder, class:^(steam_app_)`)
- EDID override for monitor if ultrawide's EDID is wrong

### Audio

- Udev rule for Rocksmith RealTone cable prevents permission issues on plug
- WirePlumber policy for Scarlett 2i2 - auto-route audio through Focusrite when plugged, back to HDMI/onboard when unplugged
- Declarative pipewire routing for RTP/SDP - network audio streams for game audio to streaming PC
- XWayland video bridge for screen sharing in Discord/Zoom under Wayland

### Network

- NetworkManager dispatcher scripts - per-SSID actions (start/stop Tailscale, sync DNS, mount NFS)
- Declarative WireGuard config - Proton VPN is imperative currently. Declarative WG or Mullvad survives rebuilds

### Auth + security

- FIDO2 for sudo + login via `security.pam.u2f` with YubiKey - passwordless sudo, natural complement to GPG + sops
- Global gitignore via home-manager - `core.excludesFile` to managed `~/.gitignore_global`
- Declarative SSH match blocks - `programs.ssh.matchBlocks` for VMs, Tailscale IPs, jump hosts
- ZRAM swap - `zramSwap.enable = true` compresses RAM for swap, lower latency less SSD wear

### Storage

- Thunderbird profile persistence to /persist for impermanence survival
- Local web server for dev - `services.nginx` + `services.phpfpm` for testing
- SATA link power management via `kernelParams = [ "ahci.mobile_lpm_policy=1" ]`

### Testing

- nixosTest for custom modules (deskmat overlay, custom NixOS modules)
- Pre-commit hook for `nix flake check`
- treefmt + nixpkgs-fmt for auto-formatting all .nix files, enforceable in CI

### Declarative apps

- Declarative flatpak config - `services.flatpak` + `systemd.user.services.flatpak-update` for GUI apps that don't need system packages
- Declarative container config via podman-compose - convert compose files to Nix (or vice versa) for single source of truth on OCI containers
- Declarative btop config - `programs.btop.settings` with layout + stylix color scheme
- tmux declarative config - persistent remote sessions over Tailscale surviving network drops

### Fleet / notifications

- Declarative input-leap / barrier for sharing mouse/keyboard between hosts
- Netdata for system monitoring - lightweight real-time dashboard for temps, GPU, disk, network. Better than Grafana for single machine
