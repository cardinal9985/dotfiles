{ config, pkgs, lib, ... }:

let
  hosts           = import ../../shared/lib/hosts.nix;
  mkPodmanNetwork = import ../../shared/lib/podman-network.nix { inherit pkgs lib; };
  mariaDBIP  = "10.89.50.10";
  bookloreIP = "10.89.50.11";
in
lib.mkMerge [
  (mkPodmanNetwork {
    name       = "booklore-net";
    containers = [ "booklore-mariadb" "booklore" ];
    subnet     = "10.89.50.0/24";
  })
  {
    systemd.tmpfiles.rules = [
      "z /persist/booklore 0755 1000 100 -"
      "d /persist/booklore/data 0755 1000 100 -"
      "d /persist/booklore/bookdrop 0755 1000 100 -"
      "d /persist/booklore/mariadb 0750 999 999 -"
    ];

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
      volumes = [ "/persist/booklore/mariadb:/var/lib/mysql" ];
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
      ports = [ "${hosts.ishimura.tailnet}:6060:6060" ];
      extraOptions = [
        "--network=booklore-net"
        "--ip=${bookloreIP}"
      ];
      dependsOn = [ "booklore-mariadb" ];
    };

    environment.persistence."/persist".directories = [
      "/persist/booklore"
    ];
  }
]
