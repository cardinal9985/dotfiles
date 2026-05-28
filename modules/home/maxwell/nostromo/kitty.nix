{ pkgs, ... }:

{
  programs.kitty = {
    enable = true;

    settings = {

      shell = "${pkgs.zsh}/bin/zsh";

      # Window
      window_padding_width = 8;
      hide_window_decorations = false;

      # Cursor
      cursor_shape = "block";
      cursor_blink_interval = 0;

      # Scrollback
      scrollback_lines = 10000;

      # Bell
      enable_audio_bell = false;
      visual_bell_duration = 0;

      # Performance
      repaint_delay = 10;
      input_delay = 3;
      sync_to_monitor = true;

      # Tabs
      tab_bar_style = "powerline";
      tab_powerline_style = "slanted";
    };
  };
}
