{ ... }:

{
  services.grafana = {
    enable = true;
    settings = {
      server = {
        http_port = 3001;
        # Bind 0.0.0.0; firewall below restricts ingress to the tailnet interface.
        http_addr = "0.0.0.0";
        domain = "grafana.ishimura.lol";
        root_url = "https://grafana.ishimura.lol";
        serve_from_sub_path = false;
      };

      analytics = {
        reporting_enabled = false;
        check_for_updates = false;
      };

      "auth.anonymous" = {
        enabled = false;
      };

      security = {
        admin_user = "admin";
        # First-run admin password. CHANGE after first login via UI.
        # Future hardening: move to sops template + admin_password_file.
        admin_password = "ishimura";
        # NixOS 26.05 removed the secret_key default. Fresh install, no
        # existing encrypted secrets in the DB, so any random fixed string
        # is safe. Hardcoded here; sops it later if you want.
        secret_key = "ishimura-grafana-secret-not-encrypting-real-secrets";
      };
    };

    provision = {
      enable = true;
      datasources.settings.datasources = [
        {
          name = "Prometheus";
          type = "prometheus";
          access = "proxy";
          url = "http://127.0.0.1:9090";
          isDefault = true;
        }
        {
          name = "Loki";
          type = "loki";
          access = "proxy";
          url = "http://127.0.0.1:3100";
        }
      ];
    };
  };

  networking.firewall.interfaces."tailscale0".allowedTCPPorts = [ 3001 ];

  # Persist Grafana's sqlite DB so dashboards, users, password changes, and
  # imported visualizations survive reboots.
  environment.persistence."/persist".directories = [
    { directory = "/var/lib/grafana"; user = "grafana"; group = "grafana"; mode = "0750"; }
  ];
}
