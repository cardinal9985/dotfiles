{ config, pkgs, ... }:

let
  # Hangar rollout (notes/specs/2026-07-07-hangar-design.md), Stage 5.
  # VS gets a native systemd unit; volume moves off Pelican into /persist.
  volume     = "/persist/gameservers/vintagestory";
  gamePort   = 42420;  # UDP - already in nostromo firewall
  maxClients = 8;
  vsServer   = "${pkgs.vintagestory}/bin/vintagestory-server";
in
{
  # /persist/gameservers dir + hangar user are declared in hangar.nix.
  systemd.tmpfiles.rules = [
    "d ${volume}                     0755 hangar hangar -"
    "d ${volume}/Saves               0755 hangar hangar -"
    "d ${volume}/Mods                0755 hangar hangar -"
    "d ${volume}/ModConfig           0755 hangar hangar -"
    "d ${volume}/Backups             0755 hangar hangar -"
    "d ${volume}/Logs                0755 hangar hangar -"
  ];

  environment.persistence."/persist".directories = [
    { directory = volume; user = "hangar"; group = "hangar"; mode = "0755"; }
  ];

  # One-shot: copy VS files out of the Pelican volume on first boot after
  # this module lands. Skipped if the destination already has a config
  # (idempotent, safe to leave enabled forever).
  systemd.services.vintagestory-migrate = {
    description = "Migrate VS files from Pelican volume (one-time)";
    wantedBy    = [ "vintagestory.service" ];
    before      = [ "vintagestory.service" ];
    serviceConfig = {
      Type            = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      set -euo pipefail
      if [ -f ${volume}/serverconfig.json ]; then
        echo "VS volume already populated - skipping migration"
        exit 0
      fi
      # Find the Pelican volume by looking for a directory that has a
      # VS-shaped serverconfig.json. `head -1` picks the first match.
      src=""
      shopt -s nullglob
      for dir in /var/lib/pelican/volumes/*/; do
        if [ -f "$dir/serverconfig.json" ] && ${pkgs.gnugrep}/bin/grep -qi "vintage\|worldname\|serverport" "$dir/serverconfig.json" 2>/dev/null; then
          src="$dir"
          break
        fi
      done
      if [ -z "$src" ]; then
        echo "No Pelican VS volume found; starting with a fresh dataPath"
        ${pkgs.coreutils}/bin/chown -R hangar:hangar ${volume}
        exit 0
      fi
      echo "Migrating VS files from $src -> ${volume}"
      ${pkgs.rsync}/bin/rsync -a "$src"/ ${volume}/
      ${pkgs.coreutils}/bin/chown -R hangar:hangar ${volume}
      echo "Migration complete"
    '';
  };

  systemd.services.vintagestory = {
    description = "Vintage Story Dedicated Server";
    after       = [ "network-online.target" "vintagestory-migrate.service" ];
    wants       = [ "network-online.target" ];
    requires    = [ "vintagestory-migrate.service" ];
    wantedBy    = [ "multi-user.target" ];

    script = ''
      cd ${volume}
      exec ${vsServer} \
        --dataPath ${volume} \
        --port ${toString gamePort} \
        --maxclients ${toString maxClients}
    '';

    serviceConfig = {
      Type            = "simple";
      User            = "hangar";
      Group           = "hangar";
      WorkingDirectory = volume;
      Restart         = "on-failure";
      RestartSec      = "10s";
      LimitNOFILE     = 1048576;
      NoNewPrivileges = true;
    };

    unitConfig = {
      StartLimitIntervalSec = "300s";
      StartLimitBurst       = "5";
    };
  };

  # Replace the wings.nix placeholder discovery entry - now VS is native.
  environment.etc."hangar/servers.d/vintage-story.json".text = builtins.toJSON {
    slug             = "vintage-story";
    homepage_slug    = "vintage-story";
    name             = "Vintage Story";
    systemd_unit     = "vintagestory.service";
    volume           = volume;
    game_type        = "vintagestory";
    connect_address  = "games.ishimura.lol:${toString gamePort}";
    config_files     = [ "serverconfig.json" ];
    # console_backend to be added in Stage 5b (stdin FIFO + log tailing).
  };
}
