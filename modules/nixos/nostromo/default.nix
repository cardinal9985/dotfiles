{ ... }:

{

  imports = [
    ./network.nix
    ./boot.nix
    ./gpu.nix
    ./steam.nix
    ./bluetooth.nix
    ./desktop.nix
    ./sops.nix
    ./stylix.nix
    ./user.nix
    ./packages.nix
    ./swap.nix
    ./impermanence.nix
  ];

}
