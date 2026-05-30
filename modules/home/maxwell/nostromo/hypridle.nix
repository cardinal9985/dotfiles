{ ... }:

{
  services.hypridle = {
    enable = true;

    settings = {
      general = {
        lock_cmd = "pidof hyprlock || hyprlock";
        ignore_dbus_inhibit = false;
      };

      listener = [
        {
          timeout = 600; # 10 min — lock
          on-timeout = "loginctl lock-session";
          on-resume = "hyprctl dispatch dpms on";
        }
        {
          timeout = 660; # 11 min — turn off display
          on-timeout = "hyprctl dispatch dpms off";
          on-resume = "hyprctl dispatch dpms on";
        }
      ];
    };
  };
}
