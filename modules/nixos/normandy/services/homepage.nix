{ inputs, ... }:

let
  hosts = import ../../shared/lib/hosts.nix;
  ishimuraTailnetIP = hosts.ishimura.tailnet;
in
{
  imports = [ inputs.homepage.nixosModules.default ];

  services.homepage = {
    enable = true;
    dataDir = "/persist/pangolin/homepage";
    hangarStatusUrl = "http://${hosts.nostromo.tailnet}:5010/public/status";

    services = [
      {
        name = "Jellyfin";
        description = "Media Server";
        url = "https://jellyfin.ishimura.lol";
        icon = "▶";
        statusPath = "/health/jellyfin";
        healthUrl = "http://${ishimuraTailnetIP}:8096/health";
      }
      {
        name = "Navidrome";
        description = "Music Streaming";
        url = "https://music.ishimura.lol";
        icon = "♪";
        statusPath = "/health/navidrome";
        healthUrl = "http://${ishimuraTailnetIP}:4533/ping";
      }
      {
        name = "BookLore";
        description = "Ebook Library";
        url = "https://books.ishimura.lol";
        icon = "❒";
        statusPath = "/health/booklore";
        healthUrl = "http://${ishimuraTailnetIP}:6060/";
      }
      {
        name = "ROMM";
        description = "Retro Games";
        url = "https://romm.ishimura.lol";
        icon = "▥";
        statusPath = "/health/romm";
        healthUrl = "http://${ishimuraTailnetIP}:8083/api/heartbeat";
      }
      {
        name = "Rec Room";
        description = "Chess, Poker, Blackjack";
        url = "https://rec.ishimura.lol";
        icon = "♞";
        statusPath = "/health/games";
        healthUrl = "http://${ishimuraTailnetIP}:5001/healthz";
      }
      {
        name = "Tools";
        description = "Dev Utilities";
        url = "https://tools.ishimura.lol";
        icon = "⚙";
        statusPath = "/health/tools";
        healthUrl = "http://${ishimuraTailnetIP}:8085/";
      }
      {
        name = "Requests";
        description = "Media Requests";
        url = "https://requests.ishimura.lol";
        icon = "✎";
        statusPath = "/health/requests";
        healthUrl = "http://${ishimuraTailnetIP}:5002/healthz";
      }
      {
        name = "Stats";
        description = "Your Stats";
        url = "https://stats.ishimura.lol";
        icon = "◍";
        statusPath = "/health/stats";
        healthUrl = "http://${ishimuraTailnetIP}:5005/healthz";
      }
      {
        name = "Search";
        description = "Meta-Search";
        url = "https://search.ishimura.lol";
        icon = "⌕";
        statusPath = "/health/search";
        healthUrl = "http://${ishimuraTailnetIP}:8888/healthz";
      }
      {
        name = "SyncTube";
        description = "Watch Together";
        url = "https://watch.ishimura.lol";
        icon = "◑";
        statusPath = "/health/synctube";
        healthUrl = "http://127.0.0.1:4545/";
      }
      {
        name = "Moodist";
        description = "Ambient Sounds";
        url = "https://moodist.ishimura.lol";
        icon = "≋";
        statusPath = "/health/moodist";
        healthUrl = "http://127.0.0.1:4546/";
      }
      {
        name = "PrivateBin";
        description = "Encrypted Pastebin";
        url = "https://paste.ishimura.lol";
        icon = "✄";
        statusPath = "/health/paste";
        healthUrl = "http://127.0.0.1:4549/";
      }
    ];

    adminServices = [
      {
        name = "Scrutiny";
        description = "Disk Health";
        url = "http://ishimura:47890";
        icon = "◉";
        statusPath = "/health/scrutiny";
        healthUrl = "http://${ishimuraTailnetIP}:47890/api/health";
      }
      {
        name = "Tdarr";
        description = "Transcoding";
        url = "http://ishimura:8265";
        icon = "⟳";
        statusPath = "/health/tdarr";
        healthUrl = "http://${ishimuraTailnetIP}:8265/api/v2/status";
      }
      {
        name = "ntfy";
        description = "Notifications";
        url = "http://normandy:8080";
        icon = "◈";
        statusPath = "/health/ntfy";
        healthUrl = "http://127.0.0.1:8080/v1/health";
      }
      {
        name = "Pangolin";
        description = "Tunnels";
        url = "https://pangolin.ishimura.lol";
        icon = "⬡";
      }
      {
        name = "Hangar";
        description = "Game Servers";
        url = "https://hangar.ishimura.lol";
        icon = "◫";
        statusPath = "/health/hangar";
        healthUrl = "http://nostromo:5010/healthz";
      }
      {
        name = "Bridge";
        description = "Fleet Control";
        url = "https://bridge.ishimura.lol";
        icon = "⎈";
        statusPath = "/health/bridge";
        healthUrl = "http://127.0.0.1:5015/health";
      }
      {
        name = "Refinery";
        description = "Media Intake";
        url = "https://refinery.ishimura.lol";
        icon = "⚒";
        statusPath = "/health/refinery";
        healthUrl = "http://${ishimuraTailnetIP}:5006/healthz";
      }
      {
        name = "VoidAuth";
        description = "Auth Provider";
        url = "https://auth.ishimura.lol";
        icon = "⊕";
        statusPath = "/health/voidauth";
        healthUrl = "http://127.0.0.1:3030/api/health";
      }
      {
        name = "AdGuard Home";
        description = "DNS + Ad Block";
        url = "http://ishimura:3000";
        icon = "⊘";
        statusPath = "/health/adguard";
        healthUrl = "http://${ishimuraTailnetIP}:3000/";
      }
      {
        name = "slskd";
        description = "Soulseek";
        url = "http://ishimura:5030";
        icon = "≈";
        statusPath = "/health/slskd";
        healthUrl = "http://${ishimuraTailnetIP}:5030/api/v0/application";
      }
      {
        name = "FileBrowser";
        description = "File Manager";
        url = "https://files.ishimura.lol";
        icon = "▤";
        statusPath = "/health/files";
        healthUrl = "http://${ishimuraTailnetIP}:8088/health";
      }
    ];

    games = [
      {
        name = "Vintage Story";
        slug = "vintage-story";
        description = "Wilderness survival sandbox in a ruined fantasy world";
        address = "games.ishimura.lol:42420";
        version = "1.22.3 (Stable)";
        icon = "▣";
        howTo = [
          "Open Vintage Story and log in with your account"
          "Click 'Multiplayer'"
          "Click 'Server connect'"
          "Paste 'games.ishimura.lol:42420' into the address field"
        ];
      }
      {
        name = "Killing Floor 2";
        slug = "killing-floor-2";
        description = "Wave-based co-op zed shooter. Bioticslab default, 6 slots";
        address = "games.ishimura.lol:7777";
        version = "1150";
        icon = "☣";
        howTo = [
          "Launch Killing Floor 2"
          "Press <b>~</b> (tilde) in-game to open the console"
          "Type <code>open games.ishimura.lol:7777</code> and hit Enter"
          "If prompted for a password, enter <b>Yw6vq8</b> If this fails just disconnect and connect again. It can be janky."
        ];
      }
      {
        name = "Escape from Tarkov: Fika";
        slug = "escape-from-tarkov-fika";
        description = "SPT (Single Player Tarkov) + Fika co-op";
        address = "https://games.ishimura.lol:6969";
        version = "SPT 4.0.13 / Fika 2.3.3";
        icon = "✪";
        howTo = [
          "Install Escape from Tarkov via the BSG launcher or other means"
          ''Download the <a href="/mods/tarkov/SPTInstaller.exe" target="_blank">SPT 4.0.13 installer</a> and install it pointing at your EFT directory''
          ''Download <a href="/mods/tarkov/mods.zip" target="_blank">mods.zip</a> and extract everything into your SPT install root''
          "Launch SPT.Launcher.exe (Wine/Proton on Linux, native on Windows)"
          "Go to settings in the top right of the SPT Launcher, turn on developer mode"
          "Change the url to 'https://games.ishimura.lol:6969'"
          "Create a profile with any name you want, pick an edition (I recommend unheard edition)"
          "In the EFT main menu, use the Fika panel to host or join a co-op session"
        ];
      }
    ];
  };

  virtualisation.oci-containers.containers.homepage = {
    image = "docker.io/library/busybox@sha256:1cfa4e2b09e127b9c4ed43578d3f3c18e7d44ea47b9ea98475c0cbe9086525f8";
    cmd = [
      "httpd"
      "-f"
      "-p"
      "80"
      "-h"
      "/www"
    ];
    volumes = [ "/persist/pangolin/homepage:/www:ro" ];
    ports = [ "127.0.0.1:8086:80" ];
    extraOptions = [ "--network=pangolin" ];
  };

  systemd.services.podman-homepage.after = [ "create-pangolin-network.service" ];
}
