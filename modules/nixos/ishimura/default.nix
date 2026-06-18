{ ... }:

{
  imports = [
    ./crowdsec.nix
    ./crowdsec-firewall-bouncer.nix
    ./dns.nix
    ./gpu.nix
    ./grafana.nix
    ./loki.nix
    ./prometheus.nix
    ./impermanence.nix
    ./booklore.nix
    ./dicebear.nix
    ./jellyfin.nix
    ./navidrome.nix
    ./pelican.nix
    ./network.nix
    ./nfs.nix
    ./newt.nix
    ./ntfy.nix
    ./packages.nix
    ./ssh.nix
    ./tdarr.nix
    ./monitoring.nix
    ./sops.nix
    ./storage.nix
    ./user.nix
    ./boot.nix
    ./substituters.nix
  ];
}
