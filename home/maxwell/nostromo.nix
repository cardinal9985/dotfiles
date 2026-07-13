{ ... }:

{
  imports = [
    ../../modules/home/maxwell/nostromo/default.nix
  ];
  home.username = "maxwell";
  home.homeDirectory = "/home/maxwell";
  home.stateVersion = "26.05";

  programs.home-manager.enable = true;
}
