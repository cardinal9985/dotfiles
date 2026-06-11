{ ... }:

{
  imports = [
    ../../modules/home/maxwell/normandy/default.nix
  ];

  home.username = "maxwell";
  home.homeDirectory = "/home/maxwell";
  home.stateVersion = "26.05";

  programs.home-manager.enable = true;
}
