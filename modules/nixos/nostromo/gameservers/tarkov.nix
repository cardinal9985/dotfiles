{ config, pkgs, ... }:

let

  volume     = "/persist/gameservers/tarkov-spt";
  pelicanSrc = "/var/lib/pelican/volumes/bb020144-8167-4da9-8cb1-252fd9ed3384";
  gamePort   = 6969;  # HTTP + WebSocket (Fika relay), already open in network.nix
in
{
  # /persist/gameservers dir + hangar user are declared in hangar.nix.
  systemd.tmpfiles.rules = [
    "d ${volume}                     0755 hangar hangar -"
  ];

  environment.persistence."/persist".directories = [
    { directory = volume; user = "hangar"; group = "hangar"; mode = "0755"; }
  ];

  systemd.services.tarkov-spt-migrate = {
    description = "Migrate SPT files from Pelican volume";
    wantedBy    = [ "tarkov-spt.service" ];
    before      = [ "tarkov-spt.service" ];
    serviceConfig = {
      Type            = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      set -euo pipefail

      if [ -x ${volume}/SPT.Server.Linux ]; then
        echo "SPT already migrated, skipping"
        exit 0
      fi

      if [ ! -d ${pelicanSrc} ]; then
        echo "warn: Pelican SPT volume ${pelicanSrc} not found - starting fresh install unsupported"
        exit 0
      fi

      echo "Migrating SPT from ${pelicanSrc} -> ${volume}"
      # -a preserves perms/mtimes/symlinks; --info=progress2 is quiet under
      # journal but useful when running manually via systemctl start.
      ${pkgs.rsync}/bin/rsync -a "${pelicanSrc}/" "${volume}/"

      # Pelican ran the container as pelican:pelican - reown to hangar so
      # the runtime unit can write logs, profiles, cache.
      ${pkgs.coreutils}/bin/chown -R hangar:hangar ${volume}
      ${pkgs.coreutils}/bin/chmod +x ${volume}/SPT.Server.Linux

      echo "SPT migration complete"
    '';
  };

  systemd.services.tarkov-spt = {
    description = "SPT (Single Player Tarkov) + Fika Server";
    after       = [ "network-online.target" "tarkov-spt-migrate.service" ];
    wants       = [ "network-online.target" ];
    requires    = [ "tarkov-spt-migrate.service" ];
    wantedBy    = [ "multi-user.target" ];

    script = ''
      cd ${volume}
      # SPT.Server.Linux is a self-contained .NET publish; it bundles
      # libcoreclr / libhostfxr / System.*.dll alongside the binary. But
      # the loader still expects a normal glibc + libstdc++ FHS layout,
      # which steam-run provides (same trick as KF2).
      exec ${pkgs.steam-run}/bin/steam-run ./SPT.Server.Linux
    '';

    serviceConfig = {
      Type             = "simple";
      User             = "hangar";
      Group            = "hangar";
      WorkingDirectory = volume;
      Restart          = "on-failure";
      RestartSec       = "10s";
      LimitNOFILE      = 1048576;
      NoNewPrivileges  = true;
    };

    unitConfig = {
      StartLimitIntervalSec = "300s";
      StartLimitBurst       = "5";
    };
  };

  environment.etc."hangar/servers.d/tarkov-spt.json".text = builtins.toJSON {
    slug             = "tarkov-spt";
    homepage_slug    = "escape-from-tarkov-fika";
    name             = "Escape from Tarkov: Fika";
    systemd_unit     = "tarkov-spt.service";
    volume           = volume;
    game_type        = "tarkov-spt";
    connect_address  = "https://games.ishimura.lol:${toString gamePort}";
    console_backend  = "spt_journal";
    console_backend_config = {
      systemd_unit = "tarkov-spt.service";
    };
  };
}
