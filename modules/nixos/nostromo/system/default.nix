{ ... }:
{
  imports = [
    ./sops.nix
    ./substituters.nix
    ./user.nix
    ./packages.nix
    ./impermanence.nix
    ./security.nix
    ./ntfy.nix
  ];
}
