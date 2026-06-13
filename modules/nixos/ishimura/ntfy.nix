{ pkgs, lib, ... }:

let
  # ── Producer 1: disk space threshold alerts ─────────────────────────────
  stateDir  = "/var/lib/disk-space-ntfy";
  stateFile = "${stateDir}/seen.txt";

  watchList = [
    "/mnt/storage:Storage union (mergerfs)"
    "/mnt/disk1:disk1"
    "/mnt/disk2:disk2"
    "/:ishimura root"
    "/persist:ishimura persist"
  ];

  thresholds = [ 85 90 95 99 ];

  diskPollScript = pkgs.writeShellScript "disk-space-ntfy-poll" ''
    set -euo pipefail
    mkdir -p ${stateDir}
    touch ${stateFile}

    new_state=$(mktemp)
    trap "rm -f $new_state" EXIT

    ${pkgs.coreutils}/bin/cat <<'EOF' | while IFS=: read -r mount label; do
${builtins.concatStringsSep "\n" watchList}
EOF
      ${pkgs.util-linux}/bin/mountpoint -q "$mount" || continue
      used_pct=$(${pkgs.coreutils}/bin/df --output=pcent "$mount" 2>/dev/null | ${pkgs.coreutils}/bin/tail -1 | ${pkgs.coreutils}/bin/tr -d ' %')
      [ -z "$used_pct" ] && continue

      crossed=""
      for t in ${toString thresholds}; do
        if [ "$used_pct" -ge "$t" ]; then
          crossed="$t"
        fi
      done
      [ -z "$crossed" ] && continue

      key="$mount:$crossed"
      echo "$key" >> "$new_state"

      if ! ${pkgs.gnugrep}/bin/grep -qFx "$key" ${stateFile}; then
        priority="default"
        [ "$crossed" -ge 95 ] && priority="high"
        [ "$crossed" -ge 99 ] && priority="urgent"

        ${pkgs.curl}/bin/curl -s \
          -H "X-Title: Disk space: $label" \
          -H "X-Priority: $priority" \
          -H "X-Tags: floppy_disk,warning" \
          -d "$label at ''${used_pct}% used (threshold $crossed%) on $mount" \
          http://normandy:8080/system >/dev/null || true
      fi
    done

    ${pkgs.coreutils}/bin/install -m 0644 "$new_state" ${stateFile}
  '';

  # ── Producer 2: OnFailure alerts for critical services on ishimura ──────
  critical = [
    "jellyfin"
    "podman-tdarr-server"
    "podman-scrutiny"
    "adguardhome"
    "unbound"
    "nfs-server"
  ];
  alertFor = name: {
    "${name}".unitConfig.OnFailure = [ "ntfy-on-failure@%n.service" ];
  };
in
{
  # ── Disk-space poller (Producer 1) ──────────────────────────────────────
  systemd.timers.disk-space-ntfy = {
    description = "Run disk-space-ntfy every 15 minutes";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "3m";
      OnUnitActiveSec = "15m";
      Unit = "disk-space-ntfy.service";
    };
  };

  # systemd.services merged: disk-space poller + per-critical OnFailure hooks
  systemd.services = lib.mkMerge ([
    {
      disk-space-ntfy = {
        description = "Poll disk usage and notify ntfy on threshold crossings";
        serviceConfig = {
          Type = "oneshot";
          ExecStart = diskPollScript;
        };
      };
    }
  ] ++ map alertFor critical);
}
