{ pkgs, lib, ... }:

let
  src = ../../../config/homepage/src;

  services = [
    {
      name        = "Jellyfin";
      description = "Media Server";
      url         = "http://100.124.97.105:8096";
      icon        = "▶";
      statusPath  = "/health/jellyfin";
      healthUrl   = "http://127.0.0.1:8096/health";
    }
  ];

  servicesJson = pkgs.writeText "services.json" (builtins.toJSON services);

  homepage = pkgs.runCommand "ishimura-homepage" {} ''
    mkdir -p $out
    cp ${src}/index.html $out/index.html
    cp ${src}/style.css  $out/style.css
    cp ${src}/app.js     $out/app.js
    cp ${src}/404.html   $out/404.html
    cp ${servicesJson}   $out/services.json
  '';

  healthLocations = builtins.listToAttrs (
    builtins.map (s: {
      name  = s.statusPath;
      value = {
        proxyPass   = s.healthUrl;
        extraConfig = ''
          proxy_connect_timeout 3s;
          proxy_read_timeout    3s;
        '';
      };
    }) (builtins.filter (s: s ? statusPath) services)
  );
in
{
  services.nginx = {
    enable = true;
    virtualHosts."ishimura.lol" = {
      default   = true;
      root      = "${homepage}";
      locations = healthLocations;
      extraConfig = ''
        error_page 404 /404.html;
      '';
    };
  };
}
