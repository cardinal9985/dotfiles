{ ... }:

{
  imports = [
    ./impermanence.nix
    ./network.nix
    ./packages.nix
    ./ssh.nix
    ./sops.nix
    ./storage.nix
    ./user.nix
    ./boot.nix
    ./substituters.nix
  ];
}
