{ ... }:

{
  imports = [
    ./hardware-configuration.nix
    ../../modules/nixos/shared/default.nix
    ../../modules/nixos/nostromo/default.nix
  ];

  system.stateVersion = "26.05";
}
