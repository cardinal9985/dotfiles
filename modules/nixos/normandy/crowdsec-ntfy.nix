{ config, pkgs, ... }:

let
  stateDir  = "/var/lib/crowdsec-ntfy";
  stateFile = "${stateDir}/seen.txt";

  pollScript = pkgs.writeShellScript "crowdsec-ntfy-poll" ''
    set -euo pipefail
    mkdir -p ${stateDir}
    touch ${stateFile}

    CONFIG=$(${pkgs.systemd}/bin/systemctl cat crowdsec | ${pkgs.gnugrep}/bin/grep -o "/nix/store/[^ ]*-crowdsec.yaml" | head -1)
    [ -z "$CONFIG" ] && exit 0

    decisions=$(${pkgs.crowdsec}/bin/cscli -c "$CONFIG" decisions list -o json 2>/dev/null || echo "[]")
    [ -z "$decisions" ] || [ "$decisions" = "null" ] && decisions="[]"

    echo "$decisions" | ${pkgs.jq}/bin/jq -r '.[].decisions[]? | "\(.id)\t\(.value)\t\(.scenario)\t\(.origin)\t\(.duration)"' | while IFS=$'\t' read -r id value scenario origin duration; do
      if ! ${pkgs.gnugrep}/bin/grep -qFx "$id" ${stateFile}; then
        ${pkgs.curl}/bin/curl -s \
          -H "X-Title: CrowdSec Ban" \
          -H "X-Tags: shield,no_entry" \
          -d "Banned $value
Scenario: $scenario
Origin: $origin
Duration: $duration" \
          http://localhost:8080/crowdsec >/dev/null || true
      fi
    done

    echo "$decisions" | ${pkgs.jq}/bin/jq -r '.[].decisions[]?.id' | sort -u > ${stateFile}.new
    mv ${stateFile}.new ${stateFile}
  '';
in
{
  systemd.services.crowdsec-ntfy = {
    description = "Poll CrowdSec decisions, post new bans to ntfy";
    after = [ "crowdsec.service" "ntfy-sh.service" ];
    serviceConfig = {
      Type = "oneshot";
      ExecStart = pollScript;
    };
  };

  systemd.timers.crowdsec-ntfy = {
    description = "Periodic CrowdSec ban → ntfy poll";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "1m";
      OnUnitActiveSec = "30s";
      AccuracySec = "5s";
    };
  };
}
