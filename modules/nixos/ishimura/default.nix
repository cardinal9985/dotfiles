{ ... }:

{
  imports = [
    ./crowdsec.nix
    ./crowdsec-firewall-bouncer.nix
    ./gpu.nix
    ./impermanence.nix
    ./jellyfin.nix
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
