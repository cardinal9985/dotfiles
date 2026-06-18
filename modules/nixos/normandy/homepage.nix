{ pkgs, ... }:

let
  src = ../../../config/homepage/src;

  # ishimura tailnet IP. Used for both click-through URLs (resolves for tailnet
  # visitors) and Normandy-side health-check proxies. Public visitors can't reach
  # this IP, that's intentional; status dot reflects reality.
  ishimuraTailnetIP = "100.92.76.121";

  # Services the public homepage advertises. Currently just Jellyfin; status is
  # checked by Normandy proxying /health/jellyfin to ishimura over the tailnet.
  services = [
    {
      name        = "Jellyfin";
      description = "Media Server";
      url         = "https://jellyfin.ishimura.lol";
      icon        = "▶";
      statusPath  = "/health/jellyfin";
      healthUrl   = "http://${ishimuraTailnetIP}:8096/health";
    }
    {
      name        = "Navidrome";
      description = "Music Streaming";
      url         = "https://music.ishimura.lol";
      icon        = "♪";
      statusPath  = "/health/navidrome";
      healthUrl   = "http://${ishimuraTailnetIP}:4533/ping";
    }
    {
      name        = "BookLore";
      description = "Ebook Library";
      url         = "https://books.ishimura.lol";
      icon        = "❒";
      statusPath  = "/health/booklore";
      healthUrl   = "http://${ishimuraTailnetIP}:6060/";
    }
    {
      name        = "ROMM";
      description = "Retro Games";
      url         = "https://romm.ishimura.lol";
      icon        = "▥";
      statusPath  = "/health/romm";
      healthUrl   = "http://${ishimuraTailnetIP}:8083/api/heartbeat";
    }
    {
      name        = "Tools";
      description = "Dev Utilities";
      url         = "https://tools.ishimura.lol";
      icon        = "⚙";
      statusPath  = "/health/tools";
      healthUrl   = "http://${ishimuraTailnetIP}:8085/";
    }
    {
      name        = "Requests";
      description = "Media Requests";
      url         = "https://requests.ishimura.lol";
      icon        = "✎";
      statusPath  = "/health/requests";
      healthUrl   = "http://${ishimuraTailnetIP}:5002/";
    }
    {
      name        = "Wrapped";
      description = "Your Stats";
      url         = "https://wrapped.ishimura.lol";
      icon        = "◍";
      statusPath  = "/health/wrapped";
      healthUrl   = "http://${ishimuraTailnetIP}:5005/health";
    }
  ];

  # Admin-only tiles. /admin/ is gated by voidauth forwardauth so only signed-in
  # admins see these.
  adminServices = [
    {
      name        = "Scrutiny";
      description = "Disk Health";
      url         = "http://ishimura:47890";
      icon        = "◉";
      statusPath  = "/health/scrutiny";
      healthUrl   = "http://${ishimuraTailnetIP}:47890/api/health";
    }
    {
      name        = "Tdarr";
      description = "Transcoding";
      url         = "http://ishimura:8265";
      icon        = "⟳";
      statusPath  = "/health/tdarr";
      healthUrl   = "http://${ishimuraTailnetIP}:8265/api/v2/status";
    }
    {
      name        = "ntfy";
      description = "Notifications";
      url         = "http://normandy:8080";
      icon        = "◈";
      statusPath  = "/health/ntfy";
      healthUrl   = "http://127.0.0.1:8080/v1/health";
    }
    {
      name        = "Pangolin";
      description = "Tunnels";
      url         = "https://pangolin.ishimura.lol";
      icon        = "⬡";
    }
    {
      name        = "Pelican";
      description = "Game Servers";
      url         = "https://pelican.ishimura.lol";
      icon        = "◆";
      statusPath  = "/health/pelican";
      healthUrl   = "http://${ishimuraTailnetIP}:8801/up";
    }
    {
      name        = "VoidAuth";
      description = "Auth Provider";
      url         = "https://auth.ishimura.lol";
      icon        = "⊕";
      statusPath  = "/health/voidauth";
      healthUrl   = "http://127.0.0.1:3030/api/health";
    }
    {
      name        = "AdGuard Home";
      description = "DNS + Ad Block";
      url         = "http://ishimura:3000";
      icon        = "⊘";
      statusPath  = "/health/adguard";
      healthUrl   = "http://${ishimuraTailnetIP}:3000/";
    }
    {
      name        = "Grafana";
      description = "Dashboards";
      url         = "http://ishimura:3001";
      icon        = "▦";
      statusPath  = "/health/grafana";
      healthUrl   = "http://${ishimuraTailnetIP}:3001/api/health";
    }
    {
      name        = "Prometheus";
      description = "Metrics";
      url         = "http://ishimura:9090";
      icon        = "◔";
      statusPath  = "/health/prometheus";
      healthUrl   = "http://${ishimuraTailnetIP}:9090/-/healthy";
    }
    {
      name        = "slskd";
      description = "Soulseek";
      url         = "http://ishimura:5030";
      icon        = "≈";
      statusPath  = "/health/slskd";
      healthUrl   = "http://${ishimuraTailnetIP}:5030/api/v0/application";
    }
  ];

  # Game servers advertised on the public homepage so friends can find the
  # connection address + a short how-to. Each card expands inline. Add new
  # games here as Pelican servers come online.
  games = [
    {
      name              = "Vintage Story";
      slug              = "vintage-story";  # matches Pelican server name (lowercased, hyphens for spaces)
      description       = "Wilderness survival sandbox in a ruined fantasy world";
      address           = "ishimura.lol:42420";
      version           = "1.22.3 (Stable)";
      icon              = "▣";
      howTo = [
        "Open Vintage Story and log in with your account"
        "Click 'Multiplayer'"
        "Click 'Server connect'"
        "Paste 'ishimura.lol:42420' into the address field"
        "Whitelist is on - ping Maxwell with your playername to be added"
      ];
    }
  ];

  servicesJson      = pkgs.writeText "services.json"       (builtins.toJSON services);
  adminServicesJson = pkgs.writeText "admin-services.json" (builtins.toJSON adminServices);
  gamesJson         = pkgs.writeText "games.json"          (builtins.toJSON games);

  homepage = pkgs.runCommand "ishimura-homepage" {} ''
    mkdir -p $out $out/admin $out/games-status
    cp ${src}/index.html       $out/index.html
    cp ${src}/style.css        $out/style.css
    cp ${src}/app.js           $out/app.js
    cp ${src}/404.html         $out/404.html
    cp ${servicesJson}         $out/services.json
    cp ${gamesJson}            $out/games.json
    cp ${src}/admin/index.html $out/admin/index.html
    cp ${adminServicesJson}    $out/admin/services.json
  '';

  # Polls Pelican Panel's application API every 30s, writes per-server
  # state JSON into the homepage's games-status/ dir. The activation script
  # uses rsync with --exclude games-status so we don't wipe these on rebuild.
  gameStatusPoller = pkgs.writeShellScript "game-status-poller" ''
    set -uo pipefail
    PATH=${pkgs.curl}/bin:${pkgs.jq}/bin:${pkgs.coreutils}/bin:${pkgs.gnused}/bin

    API_KEY=$(cat /run/secrets/pelican/application_api_key 2>/dev/null || true)
    [ -z "$API_KEY" ] && exit 0

    OUT_DIR=/persist/pangolin/homepage/games-status
    mkdir -p "$OUT_DIR"

    # Pelican Client API returns the logged-in user's servers. Each server
    # listing only gives name/identifier; live state comes from per-server
    # resources endpoint. So: list servers, then query each one's resources.
    # ptla_ keys could use /api/application/servers in one shot; ptlc_ keys
    # need this two-step. We support both transparently.
    if [[ "$API_KEY" == ptla_* ]]; then
      url="https://pelican.ishimura.lol/api/application/servers"
    else
      url="https://pelican.ishimura.lol/api/client"
    fi

    response=$(curl -s --max-time 8 \
      -H "Authorization: Bearer $API_KEY" \
      -H "Accept: application/json" \
      "$url" || echo "{}")

    # Sanity check the response is JSON, otherwise emit empty list. Some
    # error responses are plain-text "Unauthorized" which would crash jq
    # with exit 5, taking the whole systemd service down.
    if ! echo "$response" | jq -e . >/dev/null 2>&1; then
      response='{"data":[]}'
    fi

    echo "$response" | jq -c '.data[]? | .attributes // empty' 2>/dev/null | while read -r srv; do
      name=$(echo "$srv" | jq -r '.name // empty')
      identifier=$(echo "$srv" | jq -r '.identifier // empty')
      status=$(echo "$srv" | jq -r '.status // ""')

      # Application API returns .status inline. Client API needs a second
      # call to /api/client/servers/<identifier>/resources for state.
      if [ -z "$status" ] && [ -n "$identifier" ]; then
        resources=$(curl -s --max-time 5 \
          -H "Authorization: Bearer $API_KEY" \
          -H "Accept: application/json" \
          "https://pelican.ishimura.lol/api/client/servers/$identifier/resources" || echo "{}")
        if ! echo "$resources" | jq -e . >/dev/null 2>&1; then
          resources='{}'
        fi
        status=$(echo "$resources" | jq -r '.attributes.current_state // "unknown"' 2>/dev/null || echo "unknown")
      fi
      [ -z "$name" ] && continue

      # Slugify: lowercase, non-alnum -> hyphen, collapse hyphens, strip edges.
      slug=$(echo "$name" | tr '[:upper:]' '[:lower:]' \
        | sed 's/[^a-z0-9]\+/-/g; s/^-//; s/-$//')
      [ -z "$slug" ] && continue

      # Normalize Pelican states into the four homepage statuses.
      case "$status" in
        running)                    js_status=online       ;;
        offline|null|"")            js_status=offline      ;;
        installing|starting|stopping|suspending) js_status=maintenance ;;
        *)                          js_status=unknown      ;;
      esac

      echo "{\"slug\":\"$slug\",\"status\":\"$js_status\",\"raw\":\"$status\"}" \
        > "$OUT_DIR/$slug.json"
    done
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/pangolin/homepage 0755 root root -"
  ];

  system.activationScripts.homepage = ''
    mkdir -p /persist/pangolin/homepage/games-status
    ${pkgs.rsync}/bin/rsync -a --delete \
      --exclude games-status \
      ${homepage}/ /persist/pangolin/homepage/
    chmod -R a+rX /persist/pangolin/homepage
  '';

  systemd.services.game-status-poller = {
    description = "Poll Pelican Panel for game-server states";
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    serviceConfig = {
      Type = "oneshot";
      ExecStart = gameStatusPoller;
    };
  };

  systemd.timers.game-status-poller = {
    description = "Run the Pelican game-status poller every 30s";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "1m";
      OnUnitActiveSec = "30s";
      AccuracySec = "5s";
      Unit = "game-status-poller.service";
    };
  };

  virtualisation.oci-containers.containers.homepage = {
    image = "docker.io/library/busybox@sha256:1cfa4e2b09e127b9c4ed43578d3f3c18e7d44ea47b9ea98475c0cbe9086525f8";
    cmd = [ "httpd" "-f" "-p" "80" "-h" "/www" ];
    volumes = [ "/persist/pangolin/homepage:/www:ro" ];
    ports = [ "127.0.0.1:8086:80" ];
    extraOptions = [ "--network=pangolin" ];
  };

  systemd.services.podman-homepage.after = [ "create-pangolin-network.service" ];
}
