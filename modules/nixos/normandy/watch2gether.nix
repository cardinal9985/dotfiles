{ config, ... }:

{
  systemd.tmpfiles.rules = [
    "d /persist/watch2gether      0750 root root -"
    "d /persist/watch2gether/data 0750 root root -"
  ];

  sops.templates."watch2gether.env" = {
    content = ''
      SESSION_SECRET=${config.sops.placeholder."watch2gether/session_secret"}
    '';
  };

  virtualisation.oci-containers.containers.watch2gether = {
    image = "ghcr.io/robrotheram/go-watch2gether:latest";
    environmentFiles = [ config.sops.templates."watch2gether.env".path ];
    environment = {
      BASE_URL                    = "https://watch.ishimura.lol";
      LISTEN_PORT                 = "8080";
      DATABASE_PATH               = "/data";
      LOG_LEVEL                   = "info";
      DISCORD_ENABLE_NOTIFICATIONS = "false";
      DEVELOPMENT                 = "false";
    };
    volumes = [ "/persist/watch2gether/data:/data" ];
    ports   = [ "127.0.0.1:4545:8080" ];
  };
}
