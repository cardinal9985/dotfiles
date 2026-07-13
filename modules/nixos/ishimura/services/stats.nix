{ config, pkgs, ... }:

let
  src = ../../../config/stats;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    apscheduler
    pymysql
    requests
  ]);

  app = pkgs.runCommand "ishimura-stats" {} ''
    mkdir -p $out
    cp -r ${src}/app.py ${src}/db.py ${src}/poller.py ${src}/recommend.py ${src}/templates $out/
  '';
in
{
  systemd.services.navidrome.serviceConfig.UMask = pkgs.lib.mkForce "0007";
  systemd.tmpfiles.rules = [
    "d /persist/stats 0750 stats stats -"
    "z /var/lib/navidrome              0770 navidrome navidrome -"
    "z /var/lib/navidrome/navidrome.db     0660 navidrome navidrome -"
    "z /var/lib/navidrome/navidrome.db-shm 0660 navidrome navidrome -"
    "z /var/lib/navidrome/navidrome.db-wal 0660 navidrome navidrome -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/stats"; user = "stats"; group = "stats"; mode = "0750"; }
  ];

  users.users.stats = {
    isSystemUser = true;
    group = "stats";
    home = "/var/lib/stats";
    extraGroups = [ "navidrome" ];
  };
  users.groups.stats = {};

  sops.templates."stats.env" = {
    owner = "stats";
    content = ''
      STATS_DB_PATH=/persist/stats/stats.db
      STATS_WEBHOOK_SECRET=${config.sops.placeholder."stats/webhook_secret"}
      GAMES_INTERNAL_URL=http://127.0.0.1:5001
      TMDB_TOKEN=${config.sops.placeholder."requests/tmdb_token"}
      LASTFM_API_KEY=${config.sops.placeholder."stats/lastfm_api_key"}
      TWITCH_CLIENT_ID=${config.sops.placeholder."stats/twitch_client_id"}
      TWITCH_CLIENT_SECRET=${config.sops.placeholder."stats/twitch_client_secret"}
      JELLYFIN_URL=http://127.0.0.1:8096
      JELLYFIN_API_KEY=${config.sops.placeholder."stats/jellyfin_api_key"}
      NAVIDROME_DB=/var/lib/navidrome/navidrome.db
      ROMM_URL=http://127.0.0.1:8083
      ROMM_DB_HOST=10.89.60.10
      ROMM_DB_PORT=3306
      ROMM_DB_NAME=romm
      ROMM_DB_USER=romm
      ROMM_DB_PASSWORD=${config.sops.placeholder."romm/db_password"}
      BOOKLORE_DB_HOST=10.89.50.10
      BOOKLORE_DB_PORT=3306
      BOOKLORE_DB_NAME=booklore
      BOOKLORE_DB_USER=booklore
      BOOKLORE_DB_PASSWORD=${config.sops.placeholder."booklore/db_password"}
    '';
  };

  systemd.services.ishimura-stats = {
    description = "Ishimura Stats - cross-service playback/usage tracker";
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "simple";
      User = "stats";
      Group = "stats";
      EnvironmentFile = config.sops.templates."stats.env".path;
      ExecStart = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart = "on-failure";
      RestartSec = "5s";
    };
  };
}
