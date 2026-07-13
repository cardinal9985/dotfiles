{ config, pkgs, lib, ... }:

let
  hosts           = import ../../shared/lib/hosts.nix;
  mkPodmanNetwork = import ../../shared/lib/podman-network.nix { inherit pkgs lib; };
  retrySrc        = ../../../config/slskd-retry;
  retryPythonEnv  = pkgs.python3;
in
lib.mkMerge [
  (mkPodmanNetwork { name = "slskd-net"; containers = [ "slskd" ]; })
  {
    systemd.tmpfiles.rules = [
      "z /persist/slskd                          0755 maxwell users -"
      "d /persist/slskd/app                      0755 maxwell users -"
      "d /mnt/storage/downloads                  0755 maxwell users -"
      "d /mnt/storage/downloads/slskd            0755 maxwell users -"
      "d /mnt/storage/downloads/slskd/complete   0755 maxwell users -"
      "d /mnt/storage/downloads/slskd/incomplete 0755 maxwell users -"
    ];

    environment.persistence."/persist".directories = [
      { directory = "/persist/slskd"; user = "maxwell"; group = "users"; mode = "0755"; }
    ];

    sops.templates."slskd.env" = {
      content = ''
        SLSKD_SLSK_USERNAME=${config.sops.placeholder."slskd/slsk_username"}
        SLSKD_SLSK_PASSWORD=${config.sops.placeholder."slskd/slsk_password"}
      '';
    };

    virtualisation.oci-containers.containers.slskd = {
      image = "slskd/slskd:latest";
      environmentFiles = [ config.sops.templates."slskd.env".path ];
      environment = {
        TZ                       = "America/New_York";
        PUID                     = "1000";
        PGID                     = "100";
        SLSKD_NO_AUTH            = "true";
        SLSKD_REMOTE_CONFIGURATION = "true";
        SLSKD_SLSK_DESCRIPTION   = "Ishimura";
        SLSKD_SLSK_LISTEN_PORT   = "50300";
        SLSKD_SHARED_DIR         = "/music";
        SLSKD_DOWNLOADS_DIR      = "/downloads/slskd/complete";
        SLSKD_INCOMPLETE_DIR     = "/downloads/slskd/incomplete";
      };
      volumes = [
        "/persist/slskd/app:/app"
        "/mnt/storage/downloads:/downloads"
        "/mnt/storage/media/music:/music"
      ];
      ports = [
        "${hosts.ishimura.tailnet}:5030:5030"
        "50300:50300"
      ];
      extraOptions = [ "--network=slskd-net" ];
    };

    systemd.services.slskd-retry = {
      description = "Re-queue slskd downloads that finished in Completed/Rejected state";
      after       = [ "podman-slskd.service" "network-online.target" ];
      wants       = [ "network-online.target" ];
      wantedBy    = [ "multi-user.target" ];
      serviceConfig = {
        Type        = "simple";
        DynamicUser = true;
        Environment = [
          "SLSKD_URL=http://${hosts.ishimura.tailnet}:5030"
          "RETRY_INTERVAL_SECS=60"
          "RETRY_MAX_ATTEMPTS=20"
        ];
        ExecStart  = "${retryPythonEnv}/bin/python ${retrySrc}/retry.py";
        Restart    = "on-failure";
        RestartSec = "30s";
      };
    };
  }
]
