{ ... }:

{
  imports = [
    ./hardware-configuration.nix
    ../../modules/nixos/shared/default.nix
    ../../modules/nixos/nostromo/default.nix
  ];

  programs.firefox.enable = true;

  system.stateVersion = "26.05";
}
