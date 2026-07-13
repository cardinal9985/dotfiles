{ pkgs, lib, ... }:

let
  hosts           = import ../../shared/lib/hosts.nix;
  mkPodmanNetwork = import ../../shared/lib/podman-network.nix { inherit pkgs lib; };
in
lib.mkMerge [
  (mkPodmanNetwork { name = "tdarr-net"; containers = [ "tdarr-server" ]; })
  {
    systemd.tmpfiles.rules = [
      "d /persist/tdarr          0755 maxwell users -"
      "d /persist/tdarr/server   0755 maxwell users -"
      "d /persist/tdarr/configs  0755 maxwell users -"
      "d /persist/tdarr/logs     0755 maxwell users -"
      "d /mnt/storage/tdarr-cache  0755 maxwell users -"
    ];

    environment.persistence."/persist".directories = [
      { directory = "/persist/tdarr"; user = "maxwell"; group = "users"; mode = "0755"; }
    ];

    virtualisation.oci-containers.containers.tdarr-server = {
      image = "ghcr.io/haveagitgat/tdarr@sha256:61af2de3245dc71da0038f80452eb2d3b960a2f76634ded108227c6ba293aee2";
      environment = {
        TZ           = "America/New_York";
        PUID         = "1000";
        PGID         = "100";
        UMASK_SET    = "002";
        serverIP     = "0.0.0.0";
        serverPort   = "8266";
        webUIPort    = "8265";
        internalNode = "false";
        inContainer  = "true";
      };
      volumes = [
        "/persist/tdarr/server:/app/server"
        "/persist/tdarr/configs:/app/configs"
        "/persist/tdarr/logs:/app/logs"
        "/mnt/storage/tdarr-cache:/temp"
        "/mnt/storage:/media"
      ];
      ports = [
        "${hosts.ishimura.tailnet}:8265:8265"
        "${hosts.ishimura.tailnet}:8266:8266"
      ];
      extraOptions = [ "--network=tdarr-net" ];
    };
  }
]
