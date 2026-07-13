{ ... }:
{
  imports = [
    ./alerts.nix
    ./boot.nix
    ./crowdsec.nix
    ./impermanence.nix
    ./monitoring.nix
    ./packages.nix
    ./sops.nix
    ./substituters.nix
    ./user.nix
  ];
}
