{ pkgs, lib, ... }:

let
  src = ../../../config/homepage/src;

  services = [
    {
      name        = "Jellyfin";
      description = "Media Server";
      url         = "http://ishimura:8096";
      icon        = "▶";
      statusPath  = "/health/jellyfin";
      healthUrl   = "http://127.0.0.1:8096/health";
    }
  ];

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
    }) (builtins.filter (s: s ? statusPath) (services ++ adminServices))
  );
in
{
  services.nginx = {
    enable = true;
    virtualHosts."ishimura.lol" = {
      default   = true;
      root      = "${homepage}";
      locations = healthLocations // {
        "/admin/" = {
          index = "index.html";
          extraConfig = ''
            allow 100.64.0.0/10;
            deny all;
          '';
        };
      };
      extraConfig = ''
        error_page 404 /404.html;
      '';
    };
  };
}
