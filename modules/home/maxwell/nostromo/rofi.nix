{ config, pkgs, lib, ... }:

let
  s = config.lib.stylix.colors;
in
{
  stylix.targets.rofi.enable = false;

  programs.rofi = {
    enable = true;
    package = pkgs.rofi;

    font = lib.mkForce "JetBrainsMono Nerd Font 13";
    terminal = "${pkgs.kitty}/bin/kitty";

    extraConfig = {
      modi = "drun,run,window";
      show-icons = true;
      drun-display-format = "{name}";
      display-drun = "  Apps";
      display-run = "  Run";
      display-window = "  Windows";
      kb-cancel = "Escape";
    };

    theme = let
      inherit (config.lib.formats.rasi) mkLiteral;
    in {
      "*" = {
        bg = mkLiteral "#${s.base00}";
        bg-alt = mkLiteral "#${s.base01}";
        bg-hover = mkLiteral "#${s.base02}";
        border-col = mkLiteral "#${s.base03}";
        fg = mkLiteral "#${s.base05}";
        fg-alt = mkLiteral "#${s.base04}";
        accent = mkLiteral "#${s.base0B}";
        urgent = mkLiteral "#${s.base08}";

        background-color = mkLiteral "transparent";
        text-color = mkLiteral "@fg";
      };

      "window" = {
        background-color = mkLiteral "@bg";
        border = mkLiteral "1px solid";
        border-color = mkLiteral "@border-col";
        border-radius = mkLiteral "10px";
        width = mkLiteral "600px";
        padding = mkLiteral "16px";
      };

      "mainbox" = {
        background-color = mkLiteral "transparent";
        spacing = mkLiteral "8px";
      };

      "inputbar" = {
        background-color = mkLiteral "@bg-alt";
        border-radius = mkLiteral "8px";
        padding = mkLiteral "8px 12px";
        spacing = mkLiteral "8px";
        children = mkLiteral "[prompt, entry]";
      };

      "prompt" = {
        background-color = mkLiteral "transparent";
        text-color = mkLiteral "@accent";
        font = "JetBrainsMono Nerd Font 13";
      };

      "entry" = {
        background-color = mkLiteral "transparent";
        text-color = mkLiteral "@fg";
        placeholder-color = mkLiteral "@fg-alt";
        placeholder = "Search...";
      };

      "listview" = {
        background-color = mkLiteral "transparent";
        scrollbar = false;
        spacing = mkLiteral "4px";
        lines = 8;
      };

      "element" = {
        background-color = mkLiteral "transparent";
        border-radius = mkLiteral "6px";
        padding = mkLiteral "8px 12px";
        spacing = mkLiteral "8px";
        orientation = mkLiteral "horizontal";
      };

      "element selected" = {
        background-color = mkLiteral "@bg-hover";
        text-color = mkLiteral "@accent";
      };

      "element-icon" = {
        background-color = mkLiteral "transparent";
        size = mkLiteral "24px";
      };

      "element-text" = {
        background-color = mkLiteral "transparent";
        text-color = mkLiteral "inherit";
        vertical-align = mkLiteral "0.5";
      };

      "mode-switcher" = {
        background-color = mkLiteral "@bg-alt";
        border-radius = mkLiteral "8px";
        padding = mkLiteral "4px";
        spacing = mkLiteral "4px";
      };

      "button" = {
        background-color = mkLiteral "transparent";
        border-radius = mkLiteral "6px";
        padding = mkLiteral "6px 12px";
        text-color = mkLiteral "@fg-alt";
      };

      "button selected" = {
        background-color = mkLiteral "@bg-hover";
        text-color = mkLiteral "@accent";
      };
    };
  };
}
