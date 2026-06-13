{ ... }:

let
  # Tailnet CGNAT range. Pinning a single IP burned us when nostromo's
  # tailscaled was restarted and got a new IP from the control plane.
  # CIDR scope is safe because the tailnet is private and only trusted
  # nodes ever receive 100.64.0.0/10 addresses.
  tailnetCIDR = "100.64.0.0/10";
in
{
  services.nfs.server = {
    enable = true;

    # NFSv4-only (skip RPC portmapper exposure). Single export root with
    # fsid=0 so clients mount `/mnt/storage` as the NFSv4 pseudo-root.
    #
    # rw                : read/write from tailnet clients
    # sync              : write through, slower but safer (kills risk of silent
    #                     data loss on ishimura power blip while client cached)
    # no_subtree_check  : recommended for whole-filesystem exports
    # no_root_squash    : preserve UIDs from clients; needed since hosts
    #                     share the user `maxwell` (uid 1000) and we want files
    #                     created on clients to land owned by maxwell on ishimura
    exports = ''
      /mnt/storage  ${tailnetCIDR}(rw,sync,no_subtree_check,no_root_squash,fsid=0)
    '';
  };

  # Tailnet interface is already trusted via shared/tailscale.nix, so NFS
  # ports (2049/tcp for v4) are reachable from the tailnet without firewall
  # changes. Public WAN remains blocked.
}
