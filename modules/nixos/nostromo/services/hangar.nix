{ inputs, pkgs, ... }:

let
  hangar = inputs.hangar.packages.${pkgs.stdenv.hostPlatform.system}.default;

  managedUnits = [
    "kf2.service"
    "vintagestory.service"
    "tarkov-spt.service"
  ];

  systemctlBin = "/run/current-system/sw/bin/systemctl";
in
{
  users.users.hangar = {
    isSystemUser = true;
    group        = "hangar";
    extraGroups  = [ "systemd-journal" ];
    home         = "/persist/gameservers";
    description  = "Hangar game-server control panel + runtime user";
  };
  users.groups.hangar = {};

  systemd.tmpfiles.rules = [
    "d /etc/hangar           0755 root root -"
    "d /etc/hangar/servers.d 0755 root root -"
  ];

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
      HANGAR_PUBLIC_DIR    = "${hangar}/public";
    };
    serviceConfig = {
      Type             = "simple";
      User             = "hangar";
      Group            = "hangar";
      WorkingDirectory = "${hangar}/lib";
      ExecStart        = "${hangar}/bin/hangar";
      Restart          = "on-failure";
      RestartSec       = "5s";
      NoNewPrivileges  = false;
    };
  };

  networking.firewall.allowedTCPPorts = [ 5010 ];
}
