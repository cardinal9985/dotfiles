{ pkgs, ... }:

{
  programs = {
    gamescope = {
      enable = true;
      capSysNice = false;
    };

    gamemode = {
      enable = true;
      settings = {
        general = {
          renice = 10;
          ioprio = 0;
        };
        gpu = {
          apply_gpu_optimisations = "accept-responsibility";
          gpu_device = 0;
          nv_powermizer_mode = 1;
        };
        cpu = {
          park_cores = "no";
          pin_cores = "yes";
        };
        custom = {
          start = "${pkgs.libnotify}/bin/notify-send 'GameMode' 'Gaming mode enabled'";
          end   = "${pkgs.libnotify}/bin/notify-send 'GameMode' 'Gaming mode disabled'";
        };
      };
    };
  };
}
