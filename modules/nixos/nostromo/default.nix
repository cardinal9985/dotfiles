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
    ./user.nix
    ./packages.nix
    ./swap.nix
    ./impermanence.nix
  ];

}
