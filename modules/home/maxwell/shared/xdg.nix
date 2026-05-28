{ config, ... }:

{
  xdg.userDirs = {
    enable = true;
    createDirectories = true;
    desktop = "${config.home.homeDirectory}/desktop";
    download = "${config.home.homeDirectory}/downloads";
    templates = "${config.home.homeDirectory}/templates";
    publicShare = "${config.home.homeDirectory}/public";
    documents = "${config.home.homeDirectory}/documents";
    music = "${config.home.homeDirectory}/music";
    pictures = "${config.home.homeDirectory}/pictures";
    videos = "${config.home.homeDirectory}/videos";
    projects = "${config.home.homeDirectory}/projects";
  };

  home.file."games/.keep".text = "";
}
