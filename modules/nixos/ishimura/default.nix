{ ... }:
{
  imports = [
    ./crowdsec.nix
    ./dns.nix
    ./gpu.nix
    ./impermanence.nix
    ./services
    ./network.nix
    ./nfs.nix
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
