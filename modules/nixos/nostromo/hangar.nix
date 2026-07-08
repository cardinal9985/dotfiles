{ config, pkgs, ... }:

let
  src = ../../../config/hangar;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [ flask ]);

  app = pkgs.runCommand "hangar" {} ''
    mkdir -p $out
    cp ${src}/app.py ${src}/shared_auth.py $out/
    cp -r ${src}/templates ${src}/static $out/
  '';

  # Whitelist of systemd units Hangar may power-cycle. Every game module
  # that lands should append its unit here so the sudoers rule stays tight.
  managedUnits = [
    "kf2.service"
  ];

  # Absolute paths - hangar's PATH doesn't include /run/current-system.
  systemctlBin = "/run/current-system/sw/bin/systemctl";
in
{
  users.users.hangar = {
    isSystemUser = true;
    group        = "hangar";
    home         = "/persist/gameservers";
    description  = "Hangar game-server control panel + runtime user";
  };
  users.groups.hangar = {};

  systemd.tmpfiles.rules = [
    "d /etc/hangar             0755 root   root   -"
    "d /etc/hangar/servers.d   0755 root   root   -"
  ];

  # Sudoers: hangar may run systemctl {start,stop,restart} on managed
  # units only, no password. Locked down per-unit + per-verb.
  security.sudo.extraRules = [
    {
      users    = [ "hangar" ];
      commands = builtins.concatMap (u: [
        { command = "${systemctlBin} start ${u}";   options = [ "NOPASSWD" "SETENV" ]; }
        { command = "${systemctlBin} stop ${u}";    options = [ "NOPASSWD" "SETENV" ]; }
        { command = "${systemctlBin} restart ${u}"; options = [ "NOPASSWD" "SETENV" ]; }
      ]) managedUnits;
    }
  ];

  systemd.services.hangar = {
    description = "Hangar game-server control panel";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];
    environment = {
      HANGAR_DISCOVERY_DIR = "/etc/hangar/servers.d";
      HANGAR_PORT          = "5010";
      HANGAR_SYSTEMCTL     = systemctlBin;
      HANGAR_SUDO          = "/run/wrappers/bin/sudo";
    };
    serviceConfig = {
      Type             = "simple";
      User             = "hangar";
      Group            = "hangar";
      WorkingDirectory = app;
      ExecStart        = "${pythonEnv}/bin/python ${app}/app.py";
      Restart          = "on-failure";
      RestartSec       = "5s";
      NoNewPrivileges  = false;  # sudo needs setuid
    };
  };

  networking.firewall.allowedTCPPorts = [ 5010 ];
}
