{ config, pkgs, ... }:

let
  siteId   = "y5rmkmov6tg0k2q";
  endpoint = "https://pangolin.ishimura.lol";

  # nixpkgs 26.05 ships fosrl-newt 1.12.4 which uses the old WG handshake.
  # Pangolin server 1.18.4 broke compat - newt/wg/register times out forever.
  # Pin to upstream 1.13.0 until nixpkgs bumps.
  newt = pkgs.fosrl-newt.overrideAttrs (old: rec {
    version = "1.13.0";
    src = pkgs.fetchFromGitHub {
      owner = "fosrl";
      repo = "newt";
      rev = version;
      hash = "sha256-Kt7YCxHQEv1DeASPJtjAwzmAiWBrkf+XNs7aJEZvb+M=";
    };
    vendorHash = "sha256-QJ70q53k4EvLpiMY+Nm70QqaZk14V0Q1CrwWVSowdUU=";
  });
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
      exec ${newt}/bin/newt --config-file /run/newt/config.json
    '';
  };
}
