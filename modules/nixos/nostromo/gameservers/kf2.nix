{ config, pkgs, ... }:

let
  hosts        = import ../../shared/lib/hosts.nix;
  volume       = "/persist/gameservers/kf2";
  serverPort   = 7777;
  queryPort    = 27015;
  webAdminPort = 8380;  # 8080 collides with Wings' API port on nostromo
  mapName      = "kf-bioticslab";
  difficulty   = 1;  # 0 Normal, 1 Hard, 2 Suicidal, 3 Hell on Earth
  serverName   = "USG-ISHIMURA";
in
{

  systemd.tmpfiles.rules = [
    "d /persist/gameservers      0755 hangar hangar -"
    "d /persist/gameservers/kf2  0755 hangar hangar -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/persist/gameservers"; user = "hangar"; group = "hangar"; mode = "0755"; }
  ];

  environment.etc."hangar/servers.d/kf2.json".text = builtins.toJSON {
    slug             = "kf2";
    homepage_slug    = "killing-floor-2";
    name             = "Killing Floor 2";
    systemd_unit     = "kf2.service";
    volume           = volume;
    game_type        = "kf2";
    connect_address  = "games.ishimura.lol:${toString serverPort}";
    webadmin_url     = "http://${hosts.nostromo.tailnet}:${toString webAdminPort}";
    config_files     = [ "KFGame/Config/KFWeb.ini" "KFGame/Config/PCServer-KFGame.ini" ];
    console_backend  = "kf2_webadmin";
    console_backend_config = {
      url           = "http://127.0.0.1:${toString webAdminPort}";
      username      = "admin";
      password_file = config.sops.secrets."kf2/admin_password".path;
    };
    mod_backend      = "kf2_workshop";
  };

  systemd.services.kf2 = {
    description = "Killing Floor 2 Dedicated Server";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];

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
      User            = "hangar";
      Group           = "hangar";
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
