{ config, pkgs, ... }:

let
  tailnetIP = "100.92.76.121";
  # Static IPs on a dedicated podman network so romm can reach mariadb
  # without aardvark-dns (AGH holds udp/53 on every bridge).
  mariaDBIP = "10.89.60.10";
  rommIP    = "10.89.60.11";
in
{
  systemd.tmpfiles.rules = [
    "z /persist/romm           0755 1000 100 -"
    "d /persist/romm/resources 0755 1000 100 -"
    "d /persist/romm/assets    0755 1000 100 -"
    "d /persist/romm/config    0755 1000 100 -"
    "d /persist/romm/mariadb   0750 999  999 -"
  ];

  environment.persistence."/persist".directories = [
    "/persist/romm"
  ];

  systemd.services.create-romm-network = {
    description = "Create romm podman network (no DNS, static subnet)";
    wantedBy = [ "podman-romm.service" "podman-romm-mariadb.service" ];
    before   = [ "podman-romm.service" "podman-romm-mariadb.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists romm-net || \
        ${pkgs.podman}/bin/podman network create \
          --disable-dns \
          --subnet=10.89.60.0/24 \
          romm-net
    '';
  };

  sops.templates."romm-mariadb.env" = {
    content = ''
      MARIADB_ROOT_PASSWORD=${config.sops.placeholder."romm/db_password"}
      MARIADB_DATABASE=romm
      MARIADB_USER=romm
      MARIADB_PASSWORD=${config.sops.placeholder."romm/db_password"}
    '';
  };

  sops.templates."romm.env" = {
    content = ''
      ROMM_AUTH_SECRET_KEY=${config.sops.placeholder."romm/auth_secret_key"}
      DB_HOST=${mariaDBIP}
      DB_PORT=3306
      DB_NAME=romm
      DB_USER=romm
      DB_PASSWD=${config.sops.placeholder."romm/db_password"}
      TZ=America/New_York
    '';
  };

  virtualisation.oci-containers.containers = {
    romm-mariadb = {
      image = "mariadb:11.4.5";
      environmentFiles = [ config.sops.templates."romm-mariadb.env".path ];
      volumes = [
        "/persist/romm/mariadb:/var/lib/mysql"
      ];
      extraOptions = [
        "--network=romm-net"
        "--ip=${mariaDBIP}"
      ];
    };

    romm = {
      image = "rommapp/romm:latest";
      environmentFiles = [ config.sops.templates."romm.env".path ];
      volumes = [
        "/persist/romm/resources:/romm/resources"
        "/persist/romm/assets:/romm/assets"
        "/persist/romm/config:/romm/config"
        "/mnt/storage/media/roms:/romm/library"
      ];
      ports = [ "${tailnetIP}:8083:8080" ];
      extraOptions = [
        "--network=romm-net"
        "--ip=${rommIP}"
      ];
      dependsOn = [ "romm-mariadb" ];
    };
  };

  systemd.services.podman-romm-mariadb.after = [ "create-romm-network.service" ];
  systemd.services.podman-romm.after         = [ "create-romm-network.service" ];
}
