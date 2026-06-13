{ ... }:

let
  # Tailnet IPs of clients permitted to mount /mnt/storage.
  # Keep the export tightly scoped: even though the tailnet is private,
  # NFSv4 simple auth is identity-by-IP for us, so listing exact peers
  # avoids accidental exposure if a new tailnet node is added later.
  nostromoTailnetIP = "100.106.24.59";
in
{
  services.nfs.server = {
    enable = true;

    # NFSv4-only (skip RPC portmapper exposure). Single export root with
    # fsid=0 so nostromo mounts `/mnt/storage` as the NFSv4 pseudo-root.
    #
    # rw                : read/write from nostromo
    # sync              : write through, slower but safer (kills risk of silent
    #                     data loss on ishimura power blip while nostromo cached)
    # no_subtree_check  : recommended for whole-filesystem exports
    # no_root_squash    : preserve UIDs from nostromo; needed since both hosts
    #                     share the user `maxwell` (uid 1000) and we want files
    #                     created on nostromo to land owned by maxwell on ishimura
    exports = ''
      /mnt/storage  ${nostromoTailnetIP}(rw,sync,no_subtree_check,no_root_squash,fsid=0)
    '';
  };

  # Tailnet interface is already trusted via shared/tailscale.nix, so NFS
  # ports (2049/tcp for v4) are reachable from the tailnet without firewall
  # changes. Public WAN remains blocked.
}
