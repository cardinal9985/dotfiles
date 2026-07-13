{ pkgs, config, ... }:

let
  s = config.lib.stylix.colors;
  nixosIcon = "${pkgs.nixos-icons}/share/icons/hicolor/scalable/apps/nix-snowflake.svg";
in
{
  programs.waybar = {
    enable = true;

    settings = {
      mainBar = {
        layer = "top";
        position = "top";
        height = 40;
        margin-top = 8;
        margin-left = 8;
        margin-right = 8;
        spacing = 4;

        modules-left = [
          "custom/launcher"
          "hyprland/workspaces"
          "hyprland/window"
        ];

        modules-center = [
          "clock"
        ];

        modules-right = [
          "mpris"
          "tray"
          "pulseaudio"
          "bluetooth"
          "network"
          "custom/notifications"
        ];

        # Left modules
        "custom/launcher" = {
          format = "<img src='${nixosIcon}' width='20' height='20'/>";
          on-click = "rofi -show drun";
          tooltip = false;
        };

        "hyprland/workspaces" = {
          format = "{icon}";
          format-icons = {
            "1" = "I";
            "2" = "II";
            "3" = "III";
            "4" = "IV";
            "5" = "V";
          };
          persistent-workspaces = {
            "1" = [];
            "2" = [];
            "3" = [];
            "4" = [];
            "5" = [];
          };
          on-click = "activate";
        };

        "hyprland/window" = {
          format = "{title}";
          max-length = 50;
          separate-outputs = true;
        };

        # Center modules
        "clock" = {
          format = "{:%I:%M %p}";
          format-alt = "{:%A, %B %d %Y}";
          tooltip-format = "<big>{:%Y %B}</big>\n<tt><small>{calendar}</small></tt>";
          on-click = "mode";
        };

        # Right modules
        "mpris" = {
          format = "  {artist} - {title}";
          format-paused = "  {artist} - {title}";
          player = "spotify";
          max-length = 40;
          scroll-player-length = true;
          tooltip = false;
        };

        "tray" = {
          spacing = 8;
        };

        "pulseaudio" = {
          format = "{icon} {volume}%";
          format-muted = "󰝟 Muted";
          format-icons = {
            default = [ "󰕿" "󰖀" "󰕾" ];
          };
          on-click = "pavucontrol";
          scroll-step = 5;
        };

        "bluetooth" = {
          format = "󰂯";
          format-connected = "󰂱 {device_alias}";
          format-disabled = "󰂲";
          on-click = "blueman-manager";
          tooltip-format = "{controller_alias}\t{controller_address}";
          tooltip-format-connected = "{controller_alias}\t{controller_address}\n\n{device_enumerate}";
          tooltip-format-enumerate-connected = "{device_alias}\t{device_address}";
        };

        "network" = {
          format-wifi = "󰤨 {essid}";
          format-ethernet = "󰈀 Wired";
          format-disconnected = "󰤭 Disconnected";
          tooltip-format = "{ifname} via {gwaddr}";
          tooltip-format-wifi = "{essid} ({signalStrength}%)";
          on-click = "nm-connection-editor";
          max-length = 20;
        };

        "custom/notifications" = {
          format = "󰂚";
          on-click = "swaync-client -t";
          tooltip = false;
        };
      };
    };

    style = ''
      * {
        font-family: "JetBrainsMono Nerd Font";
        font-size: 13px;
        border: none;
        border-radius: 0;
        min-height: 0;
      }

      window#waybar {
        background-color: rgba(${s.base00-rgb-r}, ${s.base00-rgb-g}, ${s.base00-rgb-b}, 0.75);
        border: 1px solid rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.5);
        border-radius: 10px;
        color: #${s.base05};
      }

      .modules-left,
      .modules-center,
      .modules-right {
        padding: 0 8px;
      }

      /* Launcher */
      #custom-launcher {
        padding: 0 8px;
        color: #${s.base0D};
      }

      #custom-launcher:hover {
        color: #${s.base0B};
      }

      /* Workspaces */
      #workspaces button {
        padding: 0 6px;
        color: #${s.base03};
        background: transparent;
        border-radius: 6px;
        transition: all 0.2s ease;
      }

      #workspaces button:hover {
        background: rgba(${s.base02-rgb-r}, ${s.base02-rgb-g}, ${s.base02-rgb-b}, 0.5);
        color: #${s.base05};
      }

      #workspaces button.active {
        color: #${s.base0B};
        background: rgba(${s.base0B-rgb-r}, ${s.base0B-rgb-g}, ${s.base0B-rgb-b}, 0.15);
      }

      #workspaces button.urgent {
        color: #${s.base08};
      }

      /* Window title */
      #window {
        color: #${s.base04};
        padding: 0 8px;
      }

      /* Clock */
      #clock {
        color: #${s.base05};
        font-weight: bold;
        padding: 0 8px;
      }

      /* MPRIS */
      #mpris {
        color: #${s.base0B};
        padding: 0 8px;
      }

      /* Tray */
      #tray {
        padding: 0 4px;
      }

      #tray > .passive {
        -gtk-icon-effect: dim;
      }

      #tray > .needs-attention {
        -gtk-icon-effect: highlight;
        background-color: #${s.base08};
      }

      /* Pulseaudio */
      #pulseaudio {
        color: #${s.base0C};
        padding: 0 8px;
      }

      #pulseaudio.muted {
        color: #${s.base03};
      }

      /* Bluetooth */
      #bluetooth {
        color: #${s.base0D};
        padding: 0 8px;
      }

      #bluetooth.connected {
        color: #${s.base0B};
      }

      #bluetooth.disabled {
        color: #${s.base03};
      }

      /* Network */
      #network {
        color: #${s.base0A};
        padding: 0 8px;
      }

      #network.disconnected {
        color: #${s.base08};
      }

      /* Notifications */
      #custom-notifications {
        color: #${s.base05};
        padding: 0 8px;
      }

      /* Hover effect for right modules */
      #pulseaudio:hover,
      #bluetooth:hover,
      #network:hover,
      #custom-notifications:hover {
        background: rgba(${s.base02-rgb-r}, ${s.base02-rgb-g}, ${s.base02-rgb-b}, 0.5);
        border-radius: 6px;
      }
    '';
  };
}
