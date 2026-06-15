{ ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./disko.nix
    ../../modules/nixos/ishimura
    ../../modules/nixos/shared
  ];

  system.stateVersion = "25.05";
}
