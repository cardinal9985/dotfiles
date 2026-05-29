{ config, lib, ... }:

let
  s = config.lib.stylix.colors;
in
{
  stylix.targets.hyprlock.enable = false;

  programs.hyprlock = {
    enable = true;

    settings = {
      general = {
        disable_loading_bar = true;
        hide_cursor = true;
        grace = 0;
        no_fade_in = false;
      };

      background = lib.mkForce [
        {
          monitor = "";
          color = "rgba(${s.base00}ff)";
          blur_size = 0;
          blur_passes = 0;
        }
      ];

      label = [
        {
          monitor = "";
          text = "$TIME";
          font_family = "JetBrainsMono Nerd Font";
          font_size = 72;
          color = "rgba(${s.base05}ff)";
          position = "0, 200";
          halign = "center";
          valign = "center";
        }
        {
          monitor = "";
          text = "cmd[update:60000] date '+%A, %B %d'";
          font_family = "JetBrainsMono Nerd Font";
          font_size = 20;
          color = "rgba(${s.base04}ff)";
          position = "0, 120";
          halign = "center";
          valign = "center";
        }
      ];

      input-field = [
        {
          monitor = "";
          size = "300, 50";
          position = "0, -100";
          halign = "center";
          valign = "center";
          outline_thickness = 1;
          dots_size = 0.3;
          dots_spacing = 0.2;
          outer_color = "rgba(${s.base03}ff)";
          inner_color = "rgba(${s.base01}ff)";
          font_color = "rgba(${s.base05}ff)";
          fade_on_empty = true;
          placeholder_text = "Password...";
          check_color = "rgba(${s.base0B}ff)";
          fail_color = "rgba(${s.base08}ff)";
          fail_text = "Incorrect";
          capslock_color = "rgba(${s.base0A}ff)";
          rounding = 8;
        }
      ];
    };
  };
}
