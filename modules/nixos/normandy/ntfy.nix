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

  # ── Producer 2: TLS cert expiry watchdog ────────────────────────────────
  # Hits each public host via openssl, alerts if any cert is <14 days from
  # expiry. Catches Traefik ACME renewal failures regardless of cause.
  certHosts = [
    "ishimura.lol"
    "auth.ishimura.lol"
    "jellyfin.ishimura.lol"
    "pangolin.ishimura.lol"
  ];
  certStateDir  = "/var/lib/cert-expiry-ntfy";
  certStateFile = "${certStateDir}/seen.txt";

  certPollScript = pkgs.writeShellScript "cert-expiry-ntfy-poll" ''
    set -euo pipefail
    mkdir -p ${certStateDir}
    touch ${certStateFile}

    new_state=$(mktemp)
    trap "rm -f $new_state" EXIT

    for host in ${builtins.concatStringsSep " " certHosts}; do
      expiry=$(${pkgs.coreutils}/bin/timeout 10 ${pkgs.openssl}/bin/openssl s_client -connect "$host:443" -servername "$host" </dev/null 2>/dev/null \
        | ${pkgs.openssl}/bin/openssl x509 -noout -enddate 2>/dev/null \
        | ${pkgs.coreutils}/bin/cut -d= -f2 || true)
      [ -z "$expiry" ] && continue

      expiry_epoch=$(${pkgs.coreutils}/bin/date -d "$expiry" +%s 2>/dev/null || echo 0)
      [ "$expiry_epoch" = "0" ] && continue

      now_epoch=$(${pkgs.coreutils}/bin/date +%s)
      days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

      threshold=""
      [ "$days_left" -le 14 ] && threshold=14
      [ "$days_left" -le 7 ]  && threshold=7
      [ "$days_left" -le 1 ]  && threshold=1
      [ -z "$threshold" ] && continue

      key="$host:$threshold"
      echo "$key" >> "$new_state"

      if ! ${pkgs.gnugrep}/bin/grep -qFx "$key" ${certStateFile}; then
        priority="default"
        [ "$threshold" = "7" ] && priority="high"
        [ "$threshold" = "1" ] && priority="urgent"

        ${pkgs.curl}/bin/curl -s \
          -H "X-Title: TLS cert expiring: $host" \
          -H "X-Priority: $priority" \
          -H "X-Tags: lock,warning" \
          -d "$host certificate expires in $days_left days ($expiry)" \
          http://localhost:8080/system >/dev/null || true
      fi
    done

    ${pkgs.coreutils}/bin/install -m 0644 "$new_state" ${certStateFile}
  '';

  # ── Producer 3: voidauth pending-signup notifier ────────────────────────
  # Polls the voidauth-db postgres for users with approved=false. New IDs
  # since last poll get posted to ntfy so admin can act on them.
  # Voidauth's user table is "user" (quoted, postgres reserved word).
  voidauthStateDir  = "/var/lib/voidauth-ntfy";
  voidauthStateFile = "${voidauthStateDir}/seen.txt";

  voidauthPollScript = pkgs.writeShellScript "voidauth-ntfy-poll" ''
    set -euo pipefail
    mkdir -p ${voidauthStateDir}
    touch ${voidauthStateFile}

    rows=$(${pkgs.podman}/bin/podman exec voidauth-db psql -U voidauth -d voidauth -t -A -F $'\t' \
      -c 'SELECT id::text, username, email, "createdAt"::text FROM "user" WHERE approved = false' \
      2>/dev/null || true)
    [ -z "$rows" ] && exit 0

    new_state=$(mktemp)
    trap "rm -f $new_state" EXIT

    echo "$rows" | while IFS=$'\t' read -r id username email created; do
      [ -z "$id" ] && continue
      echo "$id" >> "$new_state"

      if ! ${pkgs.gnugrep}/bin/grep -qFx "$id" ${voidauthStateFile}; then
        ${pkgs.curl}/bin/curl -s \
          -H "X-Title: New signup pending approval" \
          -H "X-Tags: bust_in_silhouette,hourglass" \
          -d "Username: $username
Email: $email
Created: $created

Approve at https://auth.ishimura.lol/admin/" \
          http://localhost:8080/auth >/dev/null || true
      fi
    done

    ${pkgs.coreutils}/bin/install -m 0644 "$new_state" ${voidauthStateFile}
  '';

  # ── Producer 4: OnFailure alerts for critical services on Normandy ──────
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

  systemd.timers.cert-expiry-ntfy = {
    description = "Daily TLS cert expiry check";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "10m";
      OnUnitActiveSec = "12h";
      Unit = "cert-expiry-ntfy.service";
    };
  };

  systemd.timers.voidauth-ntfy = {
    description = "Watch voidauth for pending signups";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "2m";
      OnUnitActiveSec = "5m";
      Unit = "voidauth-ntfy.service";
    };
  };

  # systemd.services merged: pollers + per-critical OnFailure hooks
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
      cert-expiry-ntfy = {
        description = "Watch TLS cert expiry on public hosts";
        serviceConfig = {
          Type = "oneshot";
          ExecStart = certPollScript;
        };
      };
      voidauth-ntfy = {
        description = "Poll voidauth-db for pending-approval signups, post new ones to ntfy";
        after = [ "podman-voidauth-db.service" "ntfy-sh.service" ];
        serviceConfig = {
          Type = "oneshot";
          ExecStart = voidauthPollScript;
        };
      };
    }
  ] ++ map alertFor critical);
}
