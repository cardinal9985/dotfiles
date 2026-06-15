{ ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./disko.nix
    ../../modules/nixos/normandy
    ../../modules/nixos/shared
  ];

  system.stateVersion = "26.05";
}
