{ ... }:

{
  imports = [
    ./anubis.nix
    ./boot.nix
    ./crowdsec.nix
    ./crowdsec-firewall-bouncer.nix
    ./crowdsec-ntfy.nix
    ./homepage.nix
    ./impermanence.nix
    ./network.nix
    ./ntfy.nix
    ./pangolin.nix
    ./podman.nix
    ./sops.nix
    ./ssh.nix
    ./user.nix
    ./voidauth.nix
  ];
}
