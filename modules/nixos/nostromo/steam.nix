{ pkgs, ... }:

{
  programs = {
    steam = {
      enable = true;
      gamescopeSession.enable = true;
      remotePlay.openFirewall = false;
      dedicatedServer.openFirewall = false;
      localNetworkGameTransfers.openFirewall = false;
      package = pkgs.steam.override {
        extraPkgs = (pkgs: with pkgs; [
          gamemode
          mangohud
          xdg-user-dirs
        ]);
        extraProfile = ''
          export LD_PRELOAD="${pkgs.gamemode}/lib/libgamemodeauto.so"
        '';
      };
      extraCompatPackages = with pkgs; [
        proton-ge-bin
      ];
    };

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
          end = "${pkgs.libnotify}/bin/notify-send 'GameMode' 'Gaming mode disabled'";
        };
      };
    };
  };

  boot.kernel.sysctl = {
    "vm.max_map_count" = 2147483642;
    "kernel.sched_autogroup_enabled" = 0;
    "vm.swappiness" = 10;
    "vm.dirty_ratio" = 10;
    "vm.dirty_background_ratio" = 5;
    "fs.inotify.max_user_watches" = 1048576;
    "fs.inotify.max_user_instances" = 8192;
    "fs.inotify.max_queued_events" = 32768;
    "net.core.rmem_max" = 134217728;
    "net.core.wmem_max" = 134217728;
  };

  environment.sessionVariables = {
    STEAM_EXTRA_COMPAT_TOOLS_PATHS = "\${HOME}/.steam/root/compatibilitytools.d";
    __GL_SHADER_DISK_CACHE = "1";
    __GL_SHADER_DISK_CACHE_SKIP_CLEANUP = "1";
    __GL_MaxFramesAllowed = "1";
    PROTON_ENABLE_NVAPI = "1";
    PROTON_HIDE_NVIDIA_GPU = "0";
  };

  security.pam.loginLimits = [
    { domain = "@users"; item = "rtprio";  type = "-";    value = "95";        }
    { domain = "@users"; item = "memlock"; type = "-";    value = "unlimited"; }
    { domain = "@users"; item = "nofile";  type = "soft"; value = "524288";    }
    { domain = "@users"; item = "nofile";  type = "hard"; value = "524288";    }
  ];
}
