{ pkgs, ... }:

let
  src = ../../../config/homepage/src;

  # ishimura tailnet IP. Used for both click-through URLs (resolves for tailnet
  # visitors) and Normandy-side health-check proxies. Public visitors can't reach
  # this IP — that's intentional; status dot reflects reality.
  ishimuraTailnetIP = "100.92.76.121";

  # Services the public homepage advertises. Currently just Jellyfin; status is
  # checked by Normandy proxying /health/jellyfin to ishimura over the tailnet.
  services = [
    {
      name        = "Jellyfin";
      description = "Media Server";
      url         = "http://ishimura:8096";
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
    }
    {
      name        = "ntfy";
      description = "Notifications";
      url         = "http://normandy:8080";
      icon        = "◈";
    }
    {
      name        = "Pangolin";
      description = "Tunnels";
      url         = "https://pangolin.ishimura.lol";
      icon        = "⬡";
    }
    {
      name        = "VoidAuth";
      description = "Auth Provider";
      url         = "https://auth.ishimura.lol";
      icon        = "⊕";
    }
  ];

  servicesJson      = pkgs.writeText "services.json"       (builtins.toJSON services);
  adminServicesJson = pkgs.writeText "admin-services.json" (builtins.toJSON adminServices);

  homepage = pkgs.runCommand "ishimura-homepage" {} ''
    mkdir -p $out $out/admin
    cp ${src}/index.html       $out/index.html
    cp ${src}/style.css        $out/style.css
    cp ${src}/app.js           $out/app.js
    cp ${src}/404.html         $out/404.html
    cp ${servicesJson}         $out/services.json
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
    image = "docker.io/library/busybox:latest";
    cmd = [ "httpd" "-f" "-p" "80" "-h" "/www" ];
    volumes = [ "/persist/pangolin/homepage:/www:ro" ];
    ports = [ "127.0.0.1:8086:80" ];
    extraOptions = [ "--network=pangolin" ];
  };

  systemd.services.podman-homepage.after = [ "create-pangolin-network.service" ];
}
