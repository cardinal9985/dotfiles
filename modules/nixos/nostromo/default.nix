{ ... }:

{

  imports = [
    ./network.nix
    ./boot.nix
    ./gpu.nix
    ./audio.nix
    ./bluetooth.nix
    ./desktop.nix
    ./sops.nix
    ./stylix.nix
    ./user.nix
    ./packages.nix
    ./gaming.nix
    ./nix-settings.nix
    ./swap.nix
    ./impermanence.nix
    ./security.nix
    ./power.nix
  ];

}
