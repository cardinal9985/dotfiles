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

  # One-shot: migrate the Pelican volume if we haven't yet AND apply
  # Hangar-managed defaults on first launch only. The marker file at
  # `.hangar-initial-config` guards the config-writing step so future
  # `/serverconfig ...` changes from the in-game console persist.
  systemd.services.vintagestory-migrate = {
    description = "Migrate VS files + apply one-time defaults";
    wantedBy    = [ "vintagestory.service" ];
    before      = [ "vintagestory.service" ];
    serviceConfig = {
      Type            = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      set -euo pipefail

      # 1. Import old Pelican volume if we haven't yet.
      if [ ! -f ${volume}/serverconfig.json ]; then
        src=""
        shopt -s nullglob
        for dir in /var/lib/pelican/volumes/*/; do
          if [ -f "$dir/serverconfig.json" ] && ${pkgs.gnugrep}/bin/grep -qi "vintage\|worldname\|serverport" "$dir/serverconfig.json" 2>/dev/null; then
            src="$dir"
            break
          fi
        done
        if [ -n "$src" ]; then
          echo "Migrating VS files from $src -> ${volume}"
          ${pkgs.rsync}/bin/rsync -a "$src"/ ${volume}/
        else
          echo "No Pelican VS volume found; starting fresh"
        fi
      fi

      # 2. Apply first-launch defaults (idempotent via marker file).
      #    Both off: server open to anyone with the address, but not
      #    listed in the public server browser. Anyone with the
      #    games.ishimura.lol:42420 URL can join.
      #    Once the marker exists these are never re-applied, so admin
      #    can flip either via console/config later.
      marker=${volume}/.hangar-initial-config
      if [ ! -f "$marker" ]; then
        echo "Applying Hangar-managed VS defaults (one-time)"
        # WhitelistMode is a string enum: "Off" / "On" / "Blacklist".
        # The numeric 0 that JSON-false gets serialized to is treated as
        # invite-only at runtime (silent - no error in the log).
        ${vsServer} --dataPath ${volume} \
          --setconfig="{ WhitelistMode: 'Off', AdvertiseServer: false }" \
          || echo "warn: --setconfig exited non-zero, continuing"
        touch "$marker"
      fi

      ${pkgs.coreutils}/bin/chown -R hangar:hangar ${volume}
    '';
  };

  systemd.services.vintagestory = {
    description = "Vintage Story Dedicated Server";
    after       = [ "network-online.target" "vintagestory-migrate.service" ];
    wants       = [ "network-online.target" ];
    requires    = [ "vintagestory-migrate.service" ];
    wantedBy    = [ "multi-user.target" ];

    # Redirect VS's stdin to a named pipe so Hangar's backend can inject
    # console commands (VS has no first-party HTTP admin API). A backgrounded
    # `sleep infinity > FIFO` keeps the write end open so the reader (VS)
    # doesn't see EOF and shut down.
    script = ''
      FIFO=/run/vintagestory/stdin
      ${pkgs.coreutils}/bin/rm -f "$FIFO"
      ${pkgs.coreutils}/bin/mkfifo -m 600 "$FIFO"
      ${pkgs.coreutils}/bin/sleep infinity > "$FIFO" &
      cd ${volume}
      exec ${vsServer} \
        --dataPath ${volume} \
        --port ${toString gamePort} \
        --maxclients ${toString maxClients} \
        < "$FIFO"
    '';

    serviceConfig = {
      Type              = "simple";
      User              = "hangar";
      Group             = "hangar";
      WorkingDirectory  = volume;
      RuntimeDirectory  = "vintagestory";
      RuntimeDirectoryMode = "0755";
      Restart           = "on-failure";
      RestartSec        = "10s";
      LimitNOFILE       = 1048576;
      NoNewPrivileges   = true;
      # KillMode default (control-group) cleans up the sleeper on stop.
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
    console_backend  = "vs_stdin";
    console_backend_config = {
      fifo         = "/run/vintagestory/stdin";
      systemd_unit = "vintagestory.service";
    };
  };
}
