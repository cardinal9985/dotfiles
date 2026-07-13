{ inputs, config, pkgs, ... }:

let
  rec-room = inputs.rec-room.packages.${pkgs.stdenv.hostPlatform.system}.default;
in
{
  systemd.tmpfiles.rules = [
    "d /persist/rec-room 0750 rec-room rec-room -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/rec-room"; user = "rec-room"; group = "rec-room"; mode = "0750"; }
  ];

  users.users.rec-room = {
    isSystemUser = true;
    group        = "rec-room";
    home         = "/var/lib/rec-room";
  };
  users.groups.rec-room = {};

  sops.templates."rec-room.env" = {
    owner   = "rec-room";
    content = ''
      SECRET_KEY=${config.sops.placeholder."chess/secret_key"}
      CHESS_DISCORD_WEBHOOK=${config.sops.placeholder."chess/discord_webhook"}
      GAMES_DB_PATH=/persist/rec-room/games.db
      STOCKFISH_PATH=${pkgs.stockfish}/bin/stockfish
      STATS_WEBHOOK_URL=http://127.0.0.1:5005/webhook/games
      STATS_WEBHOOK_SECRET=${config.sops.placeholder."stats/webhook_secret"}
    '';
  };

  systemd.services.ishimura-rec-room-migrate = {
    description = "Migrate chess.db / games.db to rec-room persist dir (one-time)";
    wantedBy    = [ "ishimura-rec-room.service" ];
    before      = [ "ishimura-rec-room.service" ];
    serviceConfig = {
      Type            = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      set -euo pipefail
      TARGET=/persist/rec-room/games.db
      # chess.db -> rec-room (original migration)
      if [ ! -f "$TARGET" ] && [ -f /persist/chess/chess.db ]; then
        install -o rec-room -g rec-room -m 0640 /persist/chess/chess.db "$TARGET"
        echo "Migrated chess.db -> $TARGET"
      fi
      # games.db -> rec-room (rename migration)
      if [ ! -f "$TARGET" ] && [ -f /persist/games/games.db ]; then
        install -o rec-room -g rec-room -m 0640 /persist/games/games.db "$TARGET"
        echo "Migrated /persist/games/games.db -> $TARGET"
      fi
    '';
  };

  systemd.services.ishimura-rec-room = {
    description = "USG Ishimura Rec Room";
    after       = [ "network-online.target" "ishimura-rec-room-migrate.service" ];
    wants       = [ "network-online.target" ];
    requires    = [ "ishimura-rec-room-migrate.service" ];
    wantedBy    = [ "multi-user.target" ];
    serviceConfig = {
      Type            = "simple";
      User            = "rec-room";
      Group           = "rec-room";
      EnvironmentFile = config.sops.templates."rec-room.env".path;
      ExecStart       = "${rec-room}/bin/rec-room";
      WorkingDirectory = "${rec-room}/lib";
      Restart         = "on-failure";
      RestartSec      = "5s";
    };
  };

  networking.firewall.allowedTCPPorts = [ 5001 ];
}
