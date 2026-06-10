{ ... }:

{
  imports = [
    ./impermanence.nix
    ./jellyfin.nix
    ./network.nix
    ./packages.nix
    ./ssh.nix
    ./monitoring.nix
    ./sops.nix
    ./storage.nix
    ./user.nix
    ./boot.nix
    ./substituters.nix
  ];
}
