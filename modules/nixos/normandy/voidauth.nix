{ config, ... }:

let
  authHost = "auth.ishimura.lol";
in
{
  systemd.tmpfiles.rules = [
    "d /persist/voidauth                  0750 root root -"
    "d /persist/voidauth/config           0750 root root -"
    "d /persist/voidauth/config/branding  0750 root root -"
    "d /persist/voidauth/postgres         0700 999  999  -"
  ];

  system.activationScripts.voidauth-theme = ''
    mkdir -p /persist/voidauth/config/branding
    install -m 0644 ${../../../config/voidauth/custom.css} \
      /persist/voidauth/config/branding/custom.css
    install -m 0644 ${../../../config/voidauth/favicon.svg} \
      /persist/voidauth/config/branding/favicon.svg
    install -m 0644 ${../../../config/voidauth/logo.svg} \
      /persist/voidauth/config/branding/logo.svg
  '';

  sops.templates."voidauth.env" = {
    content = ''
      APP_URL=https://${authHost}
      APP_TITLE=USG ISHIMURA :: AUTH
      PORT=3000
      STORAGE_KEY=${config.sops.placeholder."voidauth/storage_key"}
      DB_HOST=voidauth-db
      DB_PORT=5432
      DB_NAME=voidauth
      DB_USER=voidauth
      DB_PASSWORD=${config.sops.placeholder."voidauth/db_password"}
    '';
  };

  sops.templates."voidauth-db.env" = {
    content = ''
      POSTGRES_DB=voidauth
      POSTGRES_USER=voidauth
      POSTGRES_PASSWORD=${config.sops.placeholder."voidauth/db_password"}
    '';
  };

  virtualisation.oci-containers.containers = {
    voidauth-db = {
      image = "docker.io/postgres:18";
      environmentFiles = [ config.sops.templates."voidauth-db.env".path ];
      volumes = [
        "/persist/voidauth/postgres:/var/lib/postgresql"
      ];
      extraOptions = [ "--network=pangolin" ];
    };

    voidauth = {
      image = "docker.io/voidauth/voidauth:latest";
      dependsOn = [ "voidauth-db" ];
      environmentFiles = [ config.sops.templates."voidauth.env".path ];
      volumes = [
        "/persist/voidauth/config:/app/config"
      ];
      ports = [ "127.0.0.1:3030:3000" ];
      extraOptions = [ "--network=pangolin" ];
    };
  };

  systemd.services.podman-voidauth-db.after = [ "create-pangolin-network.service" ];
  systemd.services.podman-voidauth.after    = [ "create-pangolin-network.service" ];
}
