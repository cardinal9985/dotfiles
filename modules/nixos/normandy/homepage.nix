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
  ];

  # Game servers advertised on the public homepage so friends can find the
  # connection address + a short how-to. Each card expands inline. Add new
  # games here as Pelican servers come online.
  games = [
    {
      name        = "Vintage Story";
      description = "Modded survival sandbox";
      address     = "ishimura.lol:42420";
      version     = "1.22.3 (Stable)";
      icon        = "▣";
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
    mkdir -p $out $out/admin
    cp ${src}/index.html       $out/index.html
    cp ${src}/style.css        $out/style.css
    cp ${src}/app.js           $out/app.js
    cp ${src}/404.html         $out/404.html
    cp ${servicesJson}         $out/services.json
    cp ${gamesJson}            $out/games.json
    cp ${src}/admin/index.html $out/admin/index.html
    cp ${adminServicesJson}    $out/admin/services.json
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/pangolin/homepage 0755 root root -"
  ];

  system.activationScripts.homepage = ''
    rm -rf /persist/pangolin/homepage/*
    cp -r ${homepage}/. /persist/pangolin/homepage/
    chmod -R a+rX /persist/pangolin/homepage
  '';

  virtualisation.oci-containers.containers.homepage = {
    image = "docker.io/library/busybox@sha256:1cfa4e2b09e127b9c4ed43578d3f3c18e7d44ea47b9ea98475c0cbe9086525f8";
    cmd = [ "httpd" "-f" "-p" "80" "-h" "/www" ];
    volumes = [ "/persist/pangolin/homepage:/www:ro" ];
    ports = [ "127.0.0.1:8086:80" ];
    extraOptions = [ "--network=pangolin" ];
  };

  systemd.services.podman-homepage.after = [ "create-pangolin-network.service" ];
}
