{ ... }:

{
  imports = [
    ./crowdsec.nix
    ./gpu.nix
    ./impermanence.nix
    ./jellyfin.nix
    ./network.nix
    ./newt.nix
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
