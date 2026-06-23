{ config, pkgs, ... }:

let
  src = ../../../config/slskd-retry;
  pythonEnv = pkgs.python3;
in
{
  systemd.services.slskd-retry = {
    description = "Re-queue slskd downloads that finished in Completed/Rejected state";
    after       = [ "podman-slskd.service" "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];
    serviceConfig = {
      Type        = "simple";
      DynamicUser = true;
      Environment = [
        # slskd binds 5030 to the tailnet IP only, not localhost.
        "SLSKD_URL=http://100.92.76.121:5030"
        "RETRY_INTERVAL_SECS=60"
        "RETRY_MAX_ATTEMPTS=20"
      ];
      ExecStart   = "${pythonEnv}/bin/python ${src}/retry.py";
      Restart     = "on-failure";
      RestartSec  = "30s";
    };
  };
}
