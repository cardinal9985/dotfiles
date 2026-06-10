{ ... }:

{
  imports = [
    ../../modules/home/maxwell/ishimura/default.nix
  ];

  home.username = "maxwell";
  home.homeDirectory = "/home/maxwell";
  home.stateVersion = "25.05";

  programs.home-manager.enable = true;
}
