{ pkgs, ... }:

{
  home.packages = [ pkgs.ntfy-sh ];

  xdg.configFile."ntfy/client.yml".text = ''
    default-host: http://normandy:8080
    subscribe:
      - topic: system
        command: ${pkgs.libnotify}/bin/notify-send -u low -i utilities-terminal "$NTFY_TITLE" "$NTFY_MESSAGE"
      - topic: deploy
        command: ${pkgs.libnotify}/bin/notify-send -u normal -i system-run "$NTFY_TITLE" "$NTFY_MESSAGE"
      - topic: crowdsec
        command: ${pkgs.libnotify}/bin/notify-send -u critical -i security-medium "$NTFY_TITLE" "$NTFY_MESSAGE"
      - topic: backup
        command: ${pkgs.libnotify}/bin/notify-send -u low -i drive-harddisk "$NTFY_TITLE" "$NTFY_MESSAGE"
  '';

  systemd.user.services.ntfy-bridge = {
    Unit = {
      Description = "ntfy → swaync notification bridge";
      After = [ "network-online.target" "graphical-session.target" ];
      Wants = [ "graphical-session.target" ];
    };
    Service = {
      ExecStart = "${pkgs.ntfy-sh}/bin/ntfy subscribe --from-config";
      Restart = "on-failure";
      RestartSec = 10;
    };
    Install.WantedBy = [ "graphical-session.target" ];
  };
}
