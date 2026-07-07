{ config, pkgs, ... }:

let
  # Migrated out of Pelican's volume path as part of the Hangar rollout
  # (docs/superpowers/specs/2026-07-07-hangar-design.md). Owned by pelican
  # user still since that's how the files were created; can rename the
  # user later.
  volume       = "/persist/gameservers/kf2";
  serverPort   = 7777;
  queryPort    = 27015;
  webAdminPort = 8380;  # 8080 collides with Wings' API port on nostromo
  mapName      = "kf-bioticslab";
  difficulty   = 0;  # 0 Normal, 1 Hard, 2 Suicidal, 3 Hell on Earth
  serverName   = "USG-ISHIMURA";  # spaces don't survive URL-encoded startup args
in
{
  # sops secret defined in ./sops.nix

  # Ensure /persist/gameservers exists and is walkable by pelican user for
  # any per-game module dropped in later (vintagestory.nix, tarkov-spt.nix).
  systemd.tmpfiles.rules = [
    "d /persist/gameservers 0755 root root -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/gameservers"; user = "root"; group = "root"; mode = "0755"; }
  ];

  systemd.services.kf2 = {
    description = "Killing Floor 2 Dedicated Server";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];

    # Ensure WebAdmin is enabled and on the right port every start. Case
    # matters here - KF2 writes bEnabled=False (capital F).
    preStart = ''
      set -eu
      CFG="${volume}/KFGame/Config/KFWeb.ini"
      if [ -f "$CFG" ]; then
        ${pkgs.gnused}/bin/sed -i 's/^bEnabled=.*/bEnabled=True/'                 "$CFG"
        ${pkgs.gnused}/bin/sed -i "s/^ListenPort=.*/ListenPort=${toString webAdminPort}/" "$CFG"
      fi
    '';

    script = ''
      ADMIN_PW=$(cat ${config.sops.secrets."kf2/admin_password".path})
      cd ${volume}
      # KF2 is a generic Linux ELF that expects FHS paths (libcurl,
      # libstdc++, glibc, steamclient.so, ...). steam-run provides the
      # environment the Pelican Debian image gave it for free.
      # WebAdmin toggle + port live in KFWeb.ini (see preStart), not URL args.
      exec ${pkgs.steam-run}/bin/steam-run ./Binaries/Win64/KFGameSteamServer.bin.x86_64 \
        "${mapName}?Port=${toString serverPort}?QueryPort=${toString queryPort}?AdminPassword=$ADMIN_PW?Difficulty=${toString difficulty}?ServerName=${serverName}"
    '';

    serviceConfig = {
      Type            = "simple";
      User            = "pelican";
      Group           = "pelican";
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
}
