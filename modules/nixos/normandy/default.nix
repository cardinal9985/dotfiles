{ ... }:

{
  imports = [
    ./boot.nix
    ./crowdsec.nix
    ./impermanence.nix
    ./network.nix
    ./ntfy.nix
    ./pangolin.nix
    ./podman.nix
    ./sops.nix
    ./ssh.nix
    ./user.nix
  ];
}
