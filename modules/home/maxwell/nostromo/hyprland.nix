{ pkgs, config, ... }:

let
  s = config.lib.stylix.colors;
in
{
  wayland.windowManager.hyprland = {
    enable = true;

    settings = {
      # Monitor
      monitor = ",2560x1080@200,auto,1";

      # Autostart
      exec_once = [
        "waybar"
        "swaync"
        "hyprpolkitagent"
        "swww-daemon"
        "wl-paste --type text --watch cliphist store"
        "wl-paste --type image --watch cliphist store"
        "nm-applet --indicator"
        "blueman-applet"
      ];

      "$mod" = "SUPER";

      # General
      general = {
        gaps_in = 4;
        gaps_out = 8;
        border_size = 1;
        "col.active_border" = "rgba(${s.base0B}ff)";
        "col.inactive_border" = "rgba(${s.base03}ff)";
        layout = "dwindle";
        resize_on_border = true;
      };

      # Decoration
      decoration = {
        rounding = 8;
        blur = {
          enabled = true;
          size = 6;
          passes = 3;
          new_optimizations = true;
          xray = false;
        };
        shadow = {
          enabled = true;
          range = 12;
          render_power = 3;
          "color" = "rgba(${s.base00}cc)";
        };
      };

      # Animations
      animations = {
        enabled = true;
        bezier = [
          "easeOutQuint, 0.23, 1, 0.32, 1"
          "easeInOutCubic, 0.65, 0.05, 0.35, 0.95"
          "linear, 0, 0, 1, 1"
        ];
        animation = [
          "windows, 1, 5, easeOutQuint, slide"
          "windowsOut, 1, 5, easeOutQuint, slide"
          "border, 1, 10, linear"
          "fade, 1, 5, easeOutQuint"
          "workspaces, 1, 6, easeInOutCubic, slide"
        ];
      };

      # Input
      input = {
        kb_layout = "us";
        follow_mouse = 1;
        touchpad = {
          natural_scroll = false;
        };
        sensitivity = 0;
      };

      # Layout
      dwindle = {
        pseudotile = true;
        preserve_split = true;
      };

      # Misc
      misc = {
        force_default_wallpaper = 0;
        disable_hyprland_logo = true;
      };

      # Env vars
      env = [
        "NIXOS_OZONE_WL,1"
        "QT_QPA_PLATFORM,wayland"
        "QT_WAYLAND_DISABLE_WINDOWDECORATION,1"
        "GDK_BACKEND,wayland,x11"
        "SDL_VIDEODRIVER,wayland"
        "CLUTTER_BACKEND,wayland"
        "XDG_CURRENT_DESKTOP,Hyprland"
        "XDG_SESSION_TYPE,wayland"
        "XDG_SESSION_DESKTOP,Hyprland"
      ];

      # Workspaces
      workspace = [
        "1, persistent:true"
        "2, persistent:true"
        "3, persistent:true"
        "4, persistent:true"
        "5, persistent:true"
      ];

      # Layer rules (blur for waybar and swaync)
      layerrule = [
        "blur, waybar"
        "ignorezero, waybar"
        "blur, swaync-control-center"
        "ignorezero, swaync-control-center"
        "blur, swaync-notification-window"
        "ignorezero, swaync-notification-window"
      ];

      # Keybinds
      bind = [
        # Keybind Cheatsheet
        "$mod, F1, exec, deskmat"

        # Apps
        "$mod, T, exec, kitty"
        "$mod, R, exec, rofi -show drun"
        "$mod, E, exec, dolphin"
        "$mod, B, exec, zen"
        "$mod, W, exec, waypaper"

        # Windows
        "$mod, Q, killactive"
        "$mod, F, fullscreen, 0"
        "$mod, V, togglefloating"
        "$mod, P, pseudo"
        "$mod, J, togglesplit"

        # Focus
        "$mod, left, movefocus, l"
        "$mod, right, movefocus, r"
        "$mod, up, movefocus, u"
        "$mod, down, movefocus, d"

        # Move windows
        "$mod SHIFT, left, movewindow, l"
        "$mod SHIFT, right, movewindow, r"
        "$mod SHIFT, up, movewindow, u"
        "$mod SHIFT, down, movewindow, d"

        # Workspaces
        "$mod, 1, workspace, 1"
        "$mod, 2, workspace, 2"
        "$mod, 3, workspace, 3"
        "$mod, 4, workspace, 4"
        "$mod, 5, workspace, 5"

        # Move window to workspace
        "$mod SHIFT, 1, movetoworkspace, 1"
        "$mod SHIFT, 2, movetoworkspace, 2"
        "$mod SHIFT, 3, movetoworkspace, 3"
        "$mod SHIFT, 4, movetoworkspace, 4"
        "$mod SHIFT, 5, movetoworkspace, 5"

        # Scroll workspaces
        "$mod, mouse_down, workspace, e-1"
        "$mod, mouse_up, workspace, e+1"

        # Screenshots
        "$mod, S, exec, grimblast --notify copysave area"
        "$mod SHIFT, S, exec, grimblast --notify copysave screen"

        # Replay buffer
        "$mod ALT, R, exec, gpu-screen-recorder -save"

        # Clipboard history
        "$mod, C, exec, cliphist list | rofi -dmenu | cliphist decode | wl-copy"

        # Media
        ", XF86AudioPlay, exec, playerctl play-pause"
        ", XF86AudioNext, exec, playerctl next"
        ", XF86AudioPrev, exec, playerctl previous"
        ", XF86AudioStop, exec, playerctl stop"

        # Volume
        ", XF86AudioMute, exec, wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"

        # Notification center
        "$mod, N, exec, swaync-client -t"

        # Kill Hyprland
        "$mod SHIFT, M, exit"
      ];

      # Repeatable binds
      binde = [
        ", XF86AudioRaiseVolume, exec, wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"
        ", XF86AudioLowerVolume, exec, wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"
      ];

      # Mouse binds
      bindm = [
        "$mod, mouse:272, movewindow"
        "$mod, mouse:273, resizewindow"
      ];
    };
  };
}
