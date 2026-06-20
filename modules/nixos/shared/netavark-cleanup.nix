{ pkgs, ... }:

{
  systemd.services.netavark-stale-flush = {
    description = "Flush stale netavark NAT chains at boot only";
    wantedBy = [ "podman.service" ];
    before = [ "podman.service" ];
    after = [ "network-pre.target" ];

    unitConfig = {
      ConditionPathExists = "!/run/netavark-stale-flush.done";
    };

    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStartPost = "${pkgs.coreutils}/bin/touch /run/netavark-stale-flush.done";
      ExecStart = pkgs.writeShellScript "flush-stale-netavark-nat" ''
        set -uo pipefail
        nft="${pkgs.nftables}/bin/nft"

        # Helper: delete all chains in a given table whose name matches a
        # netavark prefix. The chain list lookup itself can fail if the
        # table doesn't exist yet (fresh boot, never had a container);
        # in that case there's nothing to clean up.
        flush_table() {
          local family="$1"
          local table="$2"
          local pattern="$3"

          # Get chain names. Format: `chain <name> {`
          local chains
          chains=$($nft list table "$family" "$table" 2>/dev/null \
            | ${pkgs.gnugrep}/bin/grep -oE "chain [a-zA-Z0-9_-]+" \
            | ${pkgs.coreutils}/bin/cut -d' ' -f2 \
            | ${pkgs.gnugrep}/bin/grep -E "$pattern" || true)

          if [ -z "$chains" ]; then
            return 0
          fi

          # Two passes: first remove any rules JUMPING to each chain
          # (otherwise delete fails with "Operation not permitted"),
          # then delete the chains themselves.
          for chain in $chains; do
            # Flush rules inside the chain so it has no contents
            $nft flush chain "$family" "$table" "$chain" 2>/dev/null || true
          done

          # Now flush rules in the parent chains that jump to these
          # (NETAVARK-HOSTPORT-DNAT etc.) - cheap to just rebuild
          for chain in $chains; do
            $nft delete chain "$family" "$table" "$chain" 2>/dev/null || true
          done
        }

        # ip nat: NETAVARK-* (legacy) and nv_* (newer) chains
        flush_table ip nat '^(NETAVARK-DN-|nv_)'

        # inet netavark: nv_* and NETAVARK-* chains live here on newer
        # netavark versions
        flush_table inet netavark '^(nv_|NETAVARK)'

        # Always succeed: a missing table or already-clean state is not
        # an error worth blocking podman startup.
        exit 0
      '';
    };
  };
}
