{ pkgs, ... }:

{
  home.packages = with pkgs; [
    awww
    waypaper
  ];

  xdg.configFile."waypaper/config.ini".text = ''
    [Settings]
    language = en
    folder = ~/dotfiles/wallpapers
    wallpaper = ~/dotfiles/wallpapers/fern-1.png
    backend = awww
    monitors = All
    fill = fill
    sort = name
    color = #000000
    subfolders = False
    show_hidden = False
    show_gifs_only = False
    post_command = 
    number_of_columns = 3
    awww_transition_type = fade
    awww_transition_duration = 2
    awww_transition_fps = 60
  '';
}
