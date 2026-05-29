{ pkgs, ... }:

{
  services.hypridle = {
    enable = true;

    settings = {
      general = {
        lock_cmd = "pidof hyprlock || hyprlock";
        before_sleep_cmd = "loginctl lock-session";
        after_sleep_cmd = "hyprctl dispatch dpms on";
        ignore_dbus_inhibit = false;
      };

      listener = [
        {
          timeout = 540; # 9 min dim screen
          on-timeout = "brightnessctl -s set 20%";
          on-resume = "brightnessctl -r";
        }
        {
          timeout = 600; # 10 min lock
          on-timeout = "loginctl lock-session";
          on-resume = "hyprctl dispatch dpms on";
        }
        {
          timeout = 660; # 11 min turn off display
          on-timeout = "hyprctl dispatch dpms off";
          on-resume = "hyprctl dispatch dpms on";
        }
      ];
    };
  };
}
