{ config, pkgs, ... }:

let
  tailnetIP = "100.92.76.121";
in
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

  systemd.services.create-slskd-network = {
    description = "Create slskd podman network (no DNS)";
    wantedBy = [ "podman-slskd.service" ];
    before   = [ "podman-slskd.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists slskd-net || \
        ${pkgs.podman}/bin/podman network create --disable-dns slskd-net
    '';
  };

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
      TZ = "America/New_York";
      PUID = "1000";
      PGID = "100";
      SLSKD_NO_AUTH = "true";
      SLSKD_REMOTE_CONFIGURATION = "true";
      SLSKD_SLSK_DESCRIPTION = "Ishimura";
      SLSKD_SLSK_LISTEN_PORT = "50300";
      SLSKD_SHARED_DIR = "/music";
      SLSKD_DOWNLOADS_DIR = "/downloads/slskd/complete";
      SLSKD_INCOMPLETE_DIR = "/downloads/slskd/incomplete";
    };
    volumes = [
      "/persist/slskd/app:/app"
      "/mnt/storage/downloads:/downloads"
      "/mnt/storage/media/music:/music"
    ];
    ports = [
      "${tailnetIP}:5030:5030"
      "50300:50300"
    ];
    extraOptions = [ "--network=slskd-net" ];
  };

  systemd.services.podman-slskd.after = [ "create-slskd-network.service" ];
}
