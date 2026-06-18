{ config, pkgs, ... }:

let
  src = ../../../config/wrapped;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    apscheduler
    pymysql
    requests
  ]);

  app = pkgs.runCommand "ishimura-wrapped" {} ''
    mkdir -p $out
    cp -r ${src}/app.py ${src}/db.py ${src}/poller.py ${src}/templates $out/
  '';
in
{
  # Navidrome's data dir defaults to 0700 navidrome:navidrome which blocks
  # even group reads. Relax to 0750 + 0640 on the SQLite file so the wrapped
  # poller can open it read-only via its navidrome group membership.
  systemd.services.navidrome.serviceConfig.UMask = pkgs.lib.mkForce "0027";
  systemd.tmpfiles.rules = [
    "d /persist/wrapped 0750 wrapped wrapped -"
    "z /var/lib/navidrome 0750 navidrome navidrome -"
    "z /var/lib/navidrome/navidrome.db 0640 navidrome navidrome -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/wrapped"; user = "wrapped"; group = "wrapped"; mode = "0750"; }
  ];

  users.users.wrapped = {
    isSystemUser = true;
    group = "wrapped";
    home = "/var/lib/wrapped";
    extraGroups = [ "navidrome" ];
  };
  users.groups.wrapped = {};

  # Embed secrets directly. The original wrapped used per-secret *_FILE paths
  # with root-only sops files; reusing the existing booklore/romm secrets
  # would mean opening them up to a shared group. Inlining into a wrapped-
  # owned env template keeps the original secrets root-only.
  sops.templates."wrapped.env" = {
    owner = "wrapped";
    content = ''
      WRAPPED_DB_PATH=/persist/wrapped/wrapped.db
      JELLYFIN_URL=http://127.0.0.1:8096
      JELLYFIN_API_KEY=${config.sops.placeholder."wrapped/jellyfin_api_key"}
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

  systemd.services.ishimura-wrapped = {
    description = "Ishimura Wrapped - cross-service playback/usage stats";
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "simple";
      User = "wrapped";
      Group = "wrapped";
      EnvironmentFile = config.sops.templates."wrapped.env".path;
      ExecStart = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart = "on-failure";
      RestartSec = "5s";
    };
  };
}
