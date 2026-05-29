{ pkgs, ... }:

{
  home.packages = with pkgs; [
    swww
    waypaper
  ];

  xdg.configFile."waypaper/config.ini".text = ''
    [Settings]
    language = en
    folder = ~/dotfiles/wallpapers
    wallpaper = ~/dotfiles/wallpapers/fern-1.png
    backend = swww
    monitors = All
    fill = fill
    sort = name
    color = #000000
    subfolders = False
    show_hidden = False
    show_gifs_only = False
    post_command = 
    number_of_columns = 3
    swww_transition_type = fade
    swww_transition_duration = 2
    swww_transition_fps = 60
  '';
}
