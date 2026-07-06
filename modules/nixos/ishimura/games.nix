{ config, pkgs, ... }:

let
  src = ../../../config/games;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    flask-socketio
    simple-websocket
    chess
  ]);

  app = pkgs.runCommand "ishimura-games" {} ''
    mkdir -p $out
    cp -r ${src}/app.py ${src}/db.py ${src}/shared_auth.py ${src}/arbiter.py \
          ${src}/stats_emit.py \
          ${src}/chess_bp.py ${src}/blackjack_bp.py ${src}/war_bp.py \
          ${src}/slots_bp.py ${src}/baccarat_bp.py ${src}/dice_bp.py \
          ${src}/roulette_bp.py ${src}/connect4_bp.py ${src}/reaction_bp.py \
          ${src}/duckrace_bp.py ${src}/yahtzee_bp.py \
          ${src}/templates ${src}/static $out/
  '';
in
{
  systemd.tmpfiles.rules = [
    "d /persist/games 0750 games games -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/games"; user = "games"; group = "games"; mode = "0750"; }
  ];

  users.users.games = {
    isSystemUser = true;
    group        = "games";
    home         = "/var/lib/games";
  };
  users.groups.games = {};

  # Sops keys stay named `chess/*` (already provisioned); we just alias them
  # into the games env under new variable names.
  sops.templates."games.env" = {
    owner   = "games";
    content = ''
      SECRET_KEY=${config.sops.placeholder."chess/secret_key"}
      CHESS_DISCORD_WEBHOOK=${config.sops.placeholder."chess/discord_webhook"}
      GAMES_DB_PATH=/persist/games/games.db
      STOCKFISH_PATH=${pkgs.stockfish}/bin/stockfish
      STATS_WEBHOOK_URL=http://127.0.0.1:5005/webhook/games
      STATS_WEBHOOK_SECRET=${config.sops.placeholder."stats/webhook_secret"}
    '';
  };

  # One-shot: migrate old chess.db to games.db on first boot if it doesn't
  # already exist. Preserves the old DB file for rollback safety.
  systemd.services.ishimura-games-migrate = {
    description = "Migrate chess.db to games.db (one-time)";
    wantedBy    = [ "ishimura-games.service" ];
    before      = [ "ishimura-games.service" ];
    serviceConfig = {
      Type            = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      set -euo pipefail
      OLD=/persist/chess/chess.db
      NEW=/persist/games/games.db
      if [ ! -f "$NEW" ] && [ -f "$OLD" ]; then
        install -o games -g games -m 0640 "$OLD" "$NEW"
        echo "Migrated $OLD -> $NEW"
      fi
    '';
  };

  systemd.services.ishimura-games = {
    description = "USG Ishimura Games Terminal";
    after       = [ "network-online.target" "ishimura-games-migrate.service" ];
    wants       = [ "network-online.target" ];
    requires    = [ "ishimura-games-migrate.service" ];
    wantedBy    = [ "multi-user.target" ];
    serviceConfig = {
      Type            = "simple";
      User            = "games";
      Group           = "games";
      EnvironmentFile = config.sops.templates."games.env".path;
      ExecStart       = "${pythonEnv}/bin/python ${app}/app.py";
      WorkingDirectory = app;
      Restart         = "on-failure";
      RestartSec      = "5s";
    };
  };

  networking.firewall.allowedTCPPorts = [ 5001 ];
}
