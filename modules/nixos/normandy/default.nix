{ ... }:

{
  imports = [
    ./boot.nix
    ./crowdsec.nix
    # ./crowdsec-firewall-bouncer.nix  # TEMP DISABLED: nftables.enable broke podman networking, re-enable in set-only mode
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
