{ ... }:

{
  imports = [
    ./anubis.nix
    ./boot.nix
    ./crowdsec.nix
    ./crowdsec-firewall-bouncer.nix
    ./homepage.nix
    ./impermanence.nix
    ./network.nix
    ./ntfy.nix
    ./packages.nix
    ./pangolin.nix
    ./sops.nix
    ./ssh.nix
    ./substituters.nix
    ./user.nix
    ./voidauth.nix
  ];
}
