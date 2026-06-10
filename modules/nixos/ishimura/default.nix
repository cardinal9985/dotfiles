{ ... }:

{
  imports = [
    ./impermanence.nix
    ./network.nix
    ./packages.nix
    ./ssh.nix
    ./sops.nix
    ./storage.nix
    ./tailscale.nix
    ./user.nix
    ./boot.nix
    ./substituters.nix
  ];
}
