{ config, pkgs, ... }:

let
  src = ../../../config/hangar;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    requests
    beautifulsoup4
  ]);

  app = pkgs.runCommand "hangar" {} ''
    mkdir -p $out $out/public
    cp ${src}/app.py ${src}/shared_auth.py $out/
    cp -r ${src}/backends ${src}/templates ${src}/static $out/
    # Publicly-served assets (no voidauth). KF2 clients fetch these when
    # loading the welcome screen, so they must be reachable without a
    # browser session cookie.
    cp ${../../../config/resources/kf2-motd-banner.png} $out/public/kf2-motd-banner.png
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
    extraGroups  = [ "systemd-journal" ];  # journalctl -u <unit> for log tailing
    home         = "/persist/gameservers";
    description  = "Hangar game-server control panel + runtime user";
  };
  users.groups.hangar = {};

  systemd.tmpfiles.rules = [
    "d /etc/hangar             0755 root   root   -"
    "d /etc/hangar/servers.d   0755 root   root   -"
  ];

  # Polkit rule: hangar user can start/stop/restart the managed units via
  # systemd's D-Bus API. No sudo/setuid required - systemctl asks polkit,
  # polkit says yes for these specific units + verbs only.
  security.polkit.enable = true;
  security.polkit.extraConfig = ''
    polkit.addRule(function(action, subject) {
      if (subject.user !== "hangar") return;
      if (action.id !== "org.freedesktop.systemd1.manage-units") return;
      var unit = action.lookup("unit");
      var verb = action.lookup("verb");
      var managed = ${builtins.toJSON managedUnits};
      var allowed = ["start", "stop", "restart", "reload"];
      if (managed.indexOf(unit) < 0) return;
      if (allowed.indexOf(verb)  < 0) return;
      return polkit.Result.YES;
    });
  '';

  systemd.services.hangar = {
    description = "Hangar game-server control panel";
    after       = [ "network-online.target" ];
    wants       = [ "network-online.target" ];
    wantedBy    = [ "multi-user.target" ];
    environment = {
      HANGAR_DISCOVERY_DIR = "/etc/hangar/servers.d";
      HANGAR_PORT          = "5010";
      HANGAR_SYSTEMCTL     = systemctlBin;
      HANGAR_PUBLIC_DIR    = "${app}/public";
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
