{ pkgs, lib, ... }:

let
  # ── Producer 1: poll CrowdSec decisions, post new bans to ntfy ──────────
  stateDir  = "/var/lib/crowdsec-ntfy";
  stateFile = "${stateDir}/seen.txt";

  crowdsecPollScript = pkgs.writeShellScript "crowdsec-ntfy-poll" ''
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

  # ── Producer 2: OnFailure alerts for critical services on Normandy ──────
  critical = [
    "podman-pangolin"
    "podman-traefik"
    "podman-gerbil"
    "podman-voidauth"
    "podman-voidauth-db"
    "podman-ntfy"
    "podman-homepage"
    "podman-errorpages"
    "anubis-public"
    "anubis-homepage"
    "crowdsec"
    "crowdsec-ntfy"
  ];
  alertFor = name: {
    "${name}".unitConfig.OnFailure = [ "ntfy-on-failure@%n.service" ];
  };
in
{
  # ── ntfy server ─────────────────────────────────────────────────────────
  services.ntfy-sh = {
    enable = true;
    settings = {
      base-url = "http://normandy:8080";
      listen-http = ":8080";
      cache-file = "/var/lib/ntfy-sh/cache.db";
      cache-duration = "12h";
      attachment-cache-dir = "/var/lib/ntfy-sh/attachments";
      behind-proxy = false;
      auth-default-access = "read-write";
    };
  };

  systemd.tmpfiles.rules = [
    "d /var/lib/ntfy-sh/attachments 0750 ntfy-sh ntfy-sh -"
  ];

  # ── CrowdSec poller (Producer 1) ────────────────────────────────────────
  systemd.timers.crowdsec-ntfy = {
    description = "Periodic CrowdSec ban → ntfy poll";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "1m";
      OnUnitActiveSec = "30s";
      AccuracySec = "5s";
    };
  };

  # systemd.services merged: crowdsec poller + per-critical OnFailure hooks
  systemd.services = lib.mkMerge ([
    {
      crowdsec-ntfy = {
        description = "Poll CrowdSec decisions, post new bans to ntfy";
        after = [ "crowdsec.service" "ntfy-sh.service" ];
        serviceConfig = {
          Type = "oneshot";
          ExecStart = crowdsecPollScript;
        };
      };
    }
  ] ++ map alertFor critical);
}
