{ config, pkgs, ... }:

let
  authHost = "auth.ishimura.lol";
in
{
  # Voidauth wedges its API after some time of uptime - container stays
  # alive, DB healthy, but every /api/authz/forward-auth call times out.
  # Probable cause: DB connection pool exhausted from forwardauth requests
  # or an unhandled async exception blocked the event loop. Until we can
  # diagnose upstream, this watchdog probes the endpoint every 2 minutes
  # and restarts the container if it doesn't respond within 4s.
  systemd.services.voidauth-watchdog = {
    description = "Probe voidauth API; restart container if hung";
    serviceConfig = {
      Type = "oneshot";
      ExecStart = pkgs.writeShellScript "voidauth-watchdog" ''
        set -uo pipefail
        code=$(${pkgs.curl}/bin/curl -s --max-time 4 \
          -o /dev/null -w '%{http_code}' \
          http://127.0.0.1:3030/api/authz/forward-auth || echo "000")
        if [ "$code" = "000" ]; then
          ${pkgs.systemd}/bin/systemctl restart podman-voidauth
        fi
      '';
    };
  };

  systemd.timers.voidauth-watchdog = {
    description = "Run voidauth watchdog every 2 minutes";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "3m";
      OnUnitActiveSec = "2m";
      Unit = "voidauth-watchdog.service";
    };
  };

  systemd.tmpfiles.rules = [
    "d /persist/voidauth                  0750 root root -"
    "d /persist/voidauth/config           0750 root root -"
    "d /persist/voidauth/config/branding  0750 root root -"
    "d /persist/voidauth/postgres         0700 999  999  -"
  ];

  system.activationScripts.voidauth-theme = ''
    mkdir -p /persist/voidauth/config/branding
    install -m 0644 ${../../../config/voidauth/custom.css} \
      /persist/voidauth/config/branding/custom.css
    install -m 0644 ${../../../config/voidauth/favicon.svg} \
      /persist/voidauth/config/branding/favicon.svg
    install -m 0644 ${../../../config/voidauth/logo.svg} \
      /persist/voidauth/config/branding/logo.svg
  '';

  sops.templates."voidauth.env" = {
    content = ''
      APP_URL=https://${authHost}
      APP_TITLE=USG ISHIMURA :: AUTH
      APP_COLOR=#3a9fbf
      APP_FONT=monospace
      PORT=3000
      DEFAULT_REDIRECT=https://ishimura.lol
      SIGNUP=true
      SIGNUP_REQUIRES_APPROVAL=true
      STORAGE_KEY=${config.sops.placeholder."voidauth/storage_key"}
      DB_HOST=voidauth-db
      DB_PORT=5432
      DB_NAME=voidauth
      DB_USER=voidauth
      DB_PASSWORD=${config.sops.placeholder."voidauth/db_password"}
      LDAP_ENABLED=true
      LDAP_PORT=3890
      LDAP_BIND_DN=cn=ldap_bind,dc=voidauth
      LDAP_BIND_PASSWORD=${config.sops.placeholder."voidauth/ldap_bind_password"}
    '';
  };

  sops.templates."voidauth-db.env" = {
    content = ''
      POSTGRES_DB=voidauth
      POSTGRES_USER=voidauth
      POSTGRES_PASSWORD=${config.sops.placeholder."voidauth/db_password"}
    '';
  };

  virtualisation.oci-containers.containers = {
    voidauth-db = {
      image = "docker.io/postgres@sha256:c27c01f74af25bde5f4f0f69d01944c4fc7f0376ea53c72aa1180dd593ce1d52";
      environmentFiles = [ config.sops.templates."voidauth-db.env".path ];
      volumes = [
        "/persist/voidauth/postgres:/var/lib/postgresql"
      ];
      extraOptions = [ "--network=pangolin" ];
    };

    voidauth = {
      image = "docker.io/voidauth/voidauth@sha256:37f9b21bba348c08aaa326ec614db82b5575ce4bbd9dceaf0f6ea604f345ff25";
      dependsOn = [ "voidauth-db" ];
      environmentFiles = [ config.sops.templates."voidauth.env".path ];
      volumes = [
        "/persist/voidauth/config:/app/config"
      ];
      ports = [
        "127.0.0.1:3030:3000"
        "3890:3890"
      ];
      extraOptions = [ "--network=pangolin" ];
    };
  };

  systemd.services.podman-voidauth-db.after = [ "create-pangolin-network.service" ];
  systemd.services.podman-voidauth.after    = [ "create-pangolin-network.service" ];
}
