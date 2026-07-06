{ config, pkgs, ... }:

let
  src = ../../../config/chess;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    flask-socketio
    simple-websocket
    chess
  ]);

  app = pkgs.runCommand "ishimura-chess" {} ''
    mkdir -p $out
    cp -r ${src}/app.py ${src}/db.py ${src}/templates ${src}/static $out/
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/chess 0750 chess chess -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/chess"; user = "chess"; group = "chess"; mode = "0750"; }
  ];

  users.users.chess = {
    isSystemUser = true;
    group        = "chess";
    home         = "/var/lib/chess";
  };
  users.groups.chess = {};

  sops.templates."chess.env" = {
    owner   = "chess";
    content = ''
      SECRET_KEY=${config.sops.placeholder."chess/secret_key"}
      DISCORD_WEBHOOK=${config.sops.placeholder."chess/discord_webhook"}
      CHESS_DB_PATH=/persist/chess/chess.db
      STOCKFISH_PATH=${pkgs.stockfish}/bin/stockfish
    '';
  };

  systemd.services.ishimura-chess = {
    description = "USG Ishimura Chess Terminal";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];
    serviceConfig = {
      Type            = "simple";
      User            = "chess";
      Group           = "chess";
      EnvironmentFile = config.sops.templates."chess.env".path;
      ExecStart       = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart         = "on-failure";
      RestartSec      = "5s";
    };
  };

  networking.firewall.allowedTCPPorts = [ 5001 ];
}
