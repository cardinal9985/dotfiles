# SPT / Fika on NixOS

Single Player Tarkov (SPT) is a community mod that replaces BSG's online servers with a local one. With the Fika mod, it supports cooperative multiplayer between friends. The setup is non-trivial because EFT is a Windows-only Unity game with BepInEx hooks, plus a separate .NET 9 server that we run via Pelican.

This directory documents the full setup as we landed it:

- **[host.md](./host.md)** - Full setup for the host (you). Game install, Pelican server, Pangolin path, mods, networking, and all the gotchas we hit during initial setup. Read top-to-bottom for a fresh nostromo install.
- **[client.md](./client.md)** - Setup for friends connecting to your server. Shorter - they don't need to host anything, just install SPT+Fika and point at your endpoint.
- **[troubleshooting.md](./troubleshooting.md)** - Symptom-keyed reference for breaks. When something dies, search here.

## Current versions

- SPT: **4.0.13**
- Fika: **2.3.3** (client) / matching Project Fika Server (server-side)
- EFT base: **0.16.9.40087**
- Proton-GE: **10-34** (via `pkgs.proton-ge-bin.steamcompattool`)
- Lutris wine runner used during install: **wine-ge-8-26-x86_64**

## Endpoint

Friends connect to:

```
https://games.ishimura.lol:6969     (TCP, SPT API)
games.ishimura.lol:6790             (UDP, Fika)
```

Resolves to the home public IP (`47.198.242.37` at time of writing) via Porkbun DNS. Home router forwards `6969/TCP` and `6790/UDP` to `nostromo:192.168.254.95`. Pelican-hosted SPT.Server.Linux container binds those ports on all interfaces.

The path is **direct home → friend** (not via normandy/Pangolin) - we tried Pangolin-relayed and the Gerbil WG tunnel was too flaky for game traffic.

## Architecture

```
friend                     home router                  nostromo
    \\                          |                            |
     \\---- TCP 6969 ---------> :6969 ----> 192.168.254.95:6969 ---> Pelican container ---> SPT.Server.Linux
     \\---- UDP 6790 ---------> :6790 ----> 192.168.254.95:6790 ---> (same container)  ---> Fika.Server.dll
     /
    /         games.ishimura.lol = 47.198.242.37 (home public IP, Porkbun A record)
```

Web services (Jellyfin, etc.) still go through Pangolin on normandy. Only game traffic is direct-forwarded.

## What's where in the dotfiles

- `modules/home/maxwell/nostromo/spt.nix` - the `tarkov` / `tarkov-svm` / `tarkov-server` wrappers and desktop entries
- `modules/home/maxwell/nostromo/gaming.nix` - shared gaming deps (lutris, umu-launcher, winetricks, etc.)
- `modules/nixos/nostromo/network.nix` - firewall openings for 6969/TCP, 6790/UDP, 42420/UDP
- `modules/nixos/normandy/homepage.nix` - homepage card with connection instructions
- `modules/nixos/normandy/pangolin.nix` - has the unused tcp-6969/udp-6790 entrypoints + raw resources (leave for now or clean up later)
