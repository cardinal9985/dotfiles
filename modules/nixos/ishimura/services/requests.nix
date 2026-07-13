{ config, pkgs, ... }:

let
  src = ../../../config/requests;

  pythonEnv = pkgs.python3.withPackages (ps: [ ps.flask ]);

  app = pkgs.runCommand "ishimura-requests" {} ''
    mkdir -p $out
    cp -r ${src}/app.py ${src}/templates $out/
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/requests 0750 requests requests -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/requests"; user = "requests"; group = "requests"; mode = "0750"; }
  ];

  users.users.requests = {
    isSystemUser = true;
    group = "requests";
    home = "/var/lib/requests";
  };
  users.groups.requests = {};

  sops.templates."requests.env" = {
    owner = "requests";
    content = ''
      DB_PATH=/persist/requests/requests.db
      TMDB_TOKEN=${config.sops.placeholder."requests/tmdb_token"}
      IGDB_CLIENT_ID=${config.sops.placeholder."romm/igdb_client_id"}
      IGDB_CLIENT_SECRET=${config.sops.placeholder."romm/igdb_client_secret"}
      NTFY_URL=http://normandy:8080
      NTFY_TOPIC=ishimura-requests
      NTFY_TOKEN=
    '';
  };

  systemd.services.ishimura-requests = {
    description = "Ishimura media + game request board";
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "simple";
      User = "requests";
      Group = "requests";
      EnvironmentFile = config.sops.templates."requests.env".path;
      ExecStart = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart = "on-failure";
      RestartSec = "5s";
    };
  };
}
