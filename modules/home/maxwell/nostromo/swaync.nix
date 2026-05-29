{ config, ... }:

let
  s = config.lib.stylix.colors;
in
{
  services.swaync = {
    enable = true;

    settings = {
      positionX = "right";
      positionY = "top";
      layer = "overlay";
      layer-shell = true;
      cssPriority = "application";
      control-center-margin-top = 8;
      control-center-margin-bottom = 8;
      control-center-margin-right = 8;
      control-center-margin-left = 0;
      notification-icon-size = 64;
      notification-body-image-height = 100;
      notification-body-image-width = 200;
      timeout = 5;
      timeout-low = 2;
      timeout-critical = 0;
      fit-to-screen = false;
      control-center-width = 380;
      control-center-height = 600;
      notification-window-width = 380;
      keyboard-shortcuts = true;
      image-visibility = "when-available";
      transition-time = 200;
      hide-on-clear = false;
      hide-on-action = true;
      script-fail-notify = true;

      widgets = [
        "inhibitors"
        "title"
        "dnd"
        "notifications"
      ];

      widget-config = {
        inhibitors = {
          text = "Inhibitors";
          button-text = "Clear All";
          clear-all-button = true;
        };
        title = {
          text = "Notifications";
          clear-all-button = true;
          button-text = "Clear All";
        };
        dnd = {
          text = "Do Not Disturb";
        };
        notifications = {
          notification-visibility = {
            example-name = {
              state = "muted";
              urgency = "Low";
              app-name = "Spotify";
            };
          };
        };
      };
    };

    style = ''
      * {
        font-family: "JetBrainsMono Nerd Font";
        font-size: 13px;
      }

      .control-center,
      .notification-window {
        background: transparent;
      }

      .control-center {
        background-color: rgba(${s.base00-rgb-r}, ${s.base00-rgb-g}, ${s.base00-rgb-b}, 0.85);
        border: 1px solid rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.5);
        border-radius: 10px;
        padding: 8px;
        color: #${s.base05};
      }

      .notification {
        background-color: rgba(${s.base01-rgb-r}, ${s.base01-rgb-g}, ${s.base01-rgb-b}, 0.95);
        border: 1px solid rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.4);
        border-radius: 8px;
        padding: 8px;
        margin: 4px 0;
        color: #${s.base05};
      }

      .notification-group {
        margin: 4px 8px;
      }

      .notification-content {
        padding: 4px;
      }

      .notification-default-action {
        border-radius: 8px;
        background: transparent;
      }

      .notification-default-action:hover {
        background-color: rgba(${s.base02-rgb-r}, ${s.base02-rgb-g}, ${s.base02-rgb-b}, 0.5);
      }

      .notification-action {
        border-radius: 6px;
        color: #${s.base05};
        background-color: rgba(${s.base02-rgb-r}, ${s.base02-rgb-g}, ${s.base02-rgb-b}, 0.5);
        border: 1px solid rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.3);
        margin: 2px;
      }

      .notification-action:hover {
        background-color: rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.6);
      }

      .summary {
        font-weight: bold;
        color: #${s.base05};
      }

      .time {
        color: #${s.base03};
        font-size: 11px;
      }

      .body {
        color: #${s.base04};
      }

      .app-name {
        color: #${s.base0B};
        font-size: 11px;
      }

      /* Urgency colors */
      .critical {
        border-color: #${s.base08};
      }

      .low {
        border-color: rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.3);
      }

      /* Control center widgets */
      .widget-title {
        color: #${s.base05};
        font-size: 14px;
        font-weight: bold;
        padding: 8px 4px;
      }

      .widget-title > button {
        color: #${s.base04};
        background: transparent;
        border: 1px solid rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.4);
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 11px;
      }

      .widget-title > button:hover {
        background-color: rgba(${s.base08-rgb-r}, ${s.base08-rgb-g}, ${s.base08-rgb-b}, 0.2);
        color: #${s.base08};
        border-color: #${s.base08};
      }

      .widget-dnd {
        color: #${s.base05};
        padding: 4px;
      }

      .widget-dnd > switch {
        border-radius: 12px;
        background-color: rgba(${s.base02-rgb-r}, ${s.base02-rgb-g}, ${s.base02-rgb-b}, 0.8);
        border: 1px solid rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.4);
      }

      .widget-dnd > switch:checked {
        background-color: #${s.base0B};
      }

      .widget-dnd > switch slider {
        background-color: #${s.base05};
        border-radius: 12px;
        min-width: 20px;
        min-height: 20px;
      }

      .widget-inhibitors {
        color: #${s.base05};
        padding: 4px;
      }

      .widget-inhibitors > button {
        color: #${s.base04};
        background: transparent;
        border: 1px solid rgba(${s.base03-rgb-r}, ${s.base03-rgb-g}, ${s.base03-rgb-b}, 0.4);
        border-radius: 6px;
        padding: 4px 8px;
      }

      .widget-inhibitors > button:hover {
        background-color: rgba(${s.base02-rgb-r}, ${s.base02-rgb-g}, ${s.base02-rgb-b}, 0.5);
      }
    '';
  };
}
