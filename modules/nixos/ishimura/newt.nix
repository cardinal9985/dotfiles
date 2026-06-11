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
      RuntimeDirectory = "newt";
      RuntimeDirectoryMode = "0700";
    };

    preStart = ''
      umask 0077
      SECRET=$(cat ${config.sops.secrets."newt/secret".path})
      cat > /run/newt/config.json <<EOF
      {
        "id": "${siteId}",
        "secret": "$SECRET",
        "endpoint": "${endpoint}",
        "tlsClientCert": ""
      }
      EOF
    '';

    script = ''
      exec ${pkgs.fosrl-newt}/bin/newt --config-file /run/newt/config.json
    '';
  };
}
