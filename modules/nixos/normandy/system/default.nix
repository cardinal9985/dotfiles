{ ... }:
{
  imports = [
    ./boot.nix
    ./crowdsec.nix
    ./impermanence.nix
    ./ntfy.nix
    ./packages.nix
    ./sops.nix
    ./substituters.nix
    ./user.nix
  ];
}
