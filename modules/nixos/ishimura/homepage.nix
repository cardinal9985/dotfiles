{ pkgs, ... }:

let
  services = [
    {
      name        = "Jellyfin";
      description = "Media Server";
      url         = "http://100.124.97.105:8096";
      icon        = "▶";
    }
  ];

  homepage = pkgs.callPackage ../../../homepage { inherit services; };
in
{
  services.nginx = {
    enable = true;
    virtualHosts."ishimura.lol" = {
      default = true;
      root    = "${homepage}";
      extraConfig = ''
        error_page 404 /404.html;
      '';
    };
  };
}
