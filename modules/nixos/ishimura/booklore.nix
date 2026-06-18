{ config, pkgs, ... }:

let
  tailnetIP = "100.92.76.121";
  # Static IPs on a dedicated podman network. We can't use aardvark-dns for
  # name resolution (AGH holds udp/53 on every interface), so the BookLore
  # container reaches MariaDB by IP rather than hostname.
  mariaDBIP = "10.89.50.10";
  bookloreIP = "10.89.50.11";
in
{
  systemd.tmpfiles.rules = [
    "d /persist/booklore          0755 1000 100 -"
    "d /persist/booklore/data     0755 1000 100 -"
    "d /persist/booklore/bookdrop 0755 1000 100 -"
    "d /persist/booklore/mariadb  0755 999  999 -"  # MariaDB container UID/GID
  ];

  systemd.services.create-booklore-network = {
    description = "Create booklore podman network (no DNS, static subnet)";
    wantedBy = [ "podman-booklore.service" "podman-booklore-mariadb.service" ];
    before   = [ "podman-booklore.service" "podman-booklore-mariadb.service" ];
    after    = [ "podman.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.podman}/bin/podman network exists booklore-net || \
        ${pkgs.podman}/bin/podman network create \
          --disable-dns \
          --subnet=10.89.50.0/24 \
          booklore-net
    '';
  };

  sops.templates."booklore-mariadb.env" = {
    content = ''
      MARIADB_ROOT_PASSWORD=${config.sops.placeholder."booklore/db_password"}
      MARIADB_DATABASE=booklore
      MARIADB_USER=booklore
      MARIADB_PASSWORD=${config.sops.placeholder."booklore/db_password"}
    '';
  };

  sops.templates."booklore.env" = {
    content = ''
      USER_ID=1000
      GROUP_ID=100
      TZ=America/New_York
      DATABASE_URL=jdbc:mariadb://${mariaDBIP}:3306/booklore
      DATABASE_USERNAME=booklore
      DATABASE_PASSWORD=${config.sops.placeholder."booklore/db_password"}
      DISK_TYPE=LOCAL
    '';
  };

  virtualisation.oci-containers.containers.booklore-mariadb = {
    image = "mariadb:11.4.5";
    environmentFiles = [ config.sops.templates."booklore-mariadb.env".path ];
    volumes = [
      "/persist/booklore/mariadb:/var/lib/mysql"
    ];
    extraOptions = [
      "--network=booklore-net"
      "--ip=${mariaDBIP}"
    ];
  };

  virtualisation.oci-containers.containers.booklore = {
    image = "ghcr.io/booklore-app/booklore:latest";
    environmentFiles = [ config.sops.templates."booklore.env".path ];
    volumes = [
      "/persist/booklore/data:/app/data"
      "/mnt/storage/media/books:/books"
      "/persist/booklore/bookdrop:/bookdrop"
    ];
    ports = [ "${tailnetIP}:6060:6060" ];
    extraOptions = [
      "--network=booklore-net"
      "--ip=${bookloreIP}"
    ];
    dependsOn = [ "booklore-mariadb" ];
  };

  systemd.services.podman-booklore-mariadb.after = [ "create-booklore-network.service" ];
  systemd.services.podman-booklore.after = [ "create-booklore-network.service" ];

  environment.persistence."/persist".directories = [
    "/persist/booklore"
  ];
}
