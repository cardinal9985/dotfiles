{ config, pkgs, ... }:

let
  siteId   = "y5rmkmov6tg0k2q";
  endpoint = "https://pangolin.ishimura.lol";
in
{
  systemd.services.newt = {
    description = "Newt - Pangolin tunnel client";
    after  = [ "network-online.target" ];
    wants  = [ "network-online.target" ];
    wantedBy = [ "multi-user.target" ];

    serviceConfig = {
      Type = "simple";
      Restart = "on-failure";
      RestartSec = 10;
    };

    script = ''
      SECRET=$(cat ${config.sops.secrets."newt/secret".path})
      exec ${pkgs.fosrl-newt}/bin/newt \
        --id "${siteId}" \
        --secret "$SECRET" \
        --endpoint "${endpoint}"
    '';
  };
}
