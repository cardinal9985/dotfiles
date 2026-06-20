{ pkgs, ... }:

let
  notifyScript = pkgs.writeShellScript "ntfy-on-failure" ''
    set -euo pipefail
    unit="''${1:-unknown}"
    # systemd's %n passes "podman-jellyfin.service.service" through the @ template;
    # strip the duplicate suffix so the journalctl query and message are clean.
    unit="''${unit%.service}"
    host=$(${pkgs.inetutils}/bin/hostname)
    last_log=$(${pkgs.systemd}/bin/journalctl -u "$unit.service" -n 5 --no-pager 2>/dev/null \
      | ${pkgs.coreutils}/bin/tail -3 \
      || true)

    ${pkgs.curl}/bin/curl -s \
      -H "X-Title: Service failed on $host" \
      -H "X-Priority: high" \
      -H "X-Tags: rotating_light,warning" \
      -d "Unit: $unit

Last log lines:
$last_log" \
      http://normandy:8080/system >/dev/null || true
  '';
in
{
  systemd.services."ntfy-on-failure@" = {
    description = "Notify ntfy when systemd unit %i fails";
    serviceConfig = {
      Type = "oneshot";
      ExecStart = "${notifyScript} %i";
    };
  };
}
