{ ... }:
{
  imports = [
    ./boot.nix
    ./crowdsec.nix
    ./impermanence.nix
    ./network.nix
    ./ntfy.nix
    ./packages.nix
    ./services
    ./sops.nix
    ./ssh.nix
    ./substituters.nix
    ./user.nix
  ];
}
