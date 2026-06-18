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
    cp -r ${src}/app.py ${src}/db.py ${src}/poller.py ${src}/templates $out/
  '';
in
{
  # Navidrome's data dir defaults to 0700 navidrome:navidrome which blocks
  # even group reads. Relax to 0750 + 0640 on the SQLite file so the stats
  # poller can open it read-only via its navidrome group membership.
  systemd.services.navidrome.serviceConfig.UMask = pkgs.lib.mkForce "0027";
  systemd.tmpfiles.rules = [
    "d /persist/stats 0750 stats stats -"
    "z /var/lib/navidrome 0750 navidrome navidrome -"
    "z /var/lib/navidrome/navidrome.db 0640 navidrome navidrome -"
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

  # Embed secrets directly. The original used per-secret *_FILE paths with
  # root-only sops files; reusing the existing booklore/romm secrets would
  # mean opening them up to a shared group. Inlining into a stats-owned env
  # template keeps the original secrets root-only.
  sops.templates."stats.env" = {
    owner = "stats";
    content = ''
      STATS_DB_PATH=/persist/stats/stats.db
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
