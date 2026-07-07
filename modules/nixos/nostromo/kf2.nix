{ config, pkgs, ... }:

let
  # Existing Pelican-installed volume - stays owned by pelican:pelican so
  # we can flip back to Wings-managed the day the attach bug is fixed.
  volume       = "/var/lib/pelican/volumes/7ecd8608-d111-4bf5-aab0-965c6eb6c0b7";
  serverPort   = 7777;
  queryPort    = 27015;
  webAdminPort = 8080;
  mapName      = "kf-bioticslab";
  difficulty   = 0;  # 0 Normal, 1 Hard, 2 Suicidal, 3 Hell on Earth
  serverName   = "USG-ISHIMURA";  # spaces don't survive URL-encoded startup args
in
{
  # sops secret defined in ./sops.nix
  systemd.services.kf2 = {
    description = "Killing Floor 2 Dedicated Server";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];

    # Ensure WebAdmin is enabled and on the right port every start. First
    # boot generates the ini with bEnabled=false; second boot picks it up.
    preStart = ''
      set -eu
      CFG="${volume}/KFGame/Config/LinuxServer-KFWeb.ini"
      if [ -f "$CFG" ]; then
        ${pkgs.gnused}/bin/sed -i 's/^bEnabled=.*/bEnabled=true/' "$CFG"
        ${pkgs.gnused}/bin/sed -i "s/^ListenPort=.*/ListenPort=${toString webAdminPort}/" "$CFG"
      fi
    '';

    script = ''
      ADMIN_PW=$(cat ${config.sops.secrets."kf2/admin_password".path})
      cd ${volume}
      exec ./Binaries/Win64/KFGameSteamServer.bin.x86_64 \
        "${mapName}?Port=${toString serverPort}?QueryPort=${toString queryPort}?AdminPassword=$ADMIN_PW?Difficulty=${toString difficulty}?ServerName=${serverName}?bWebServer=true?WebAdminPort=${toString webAdminPort}"
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
