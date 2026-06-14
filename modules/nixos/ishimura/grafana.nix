{ config, ... }:

{
  sops.secrets."grafana/secret_key" = {
    owner = "grafana";
    group = "grafana";
    mode = "0400";
  };

  sops.secrets."grafana/admin_password" = {
    owner = "grafana";
    group = "grafana";
    mode = "0400";
  };

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

      # Grafana 13 stores dashboards via a new Kubernetes-style API
      # (dashboard.grafana.app) which doesn't always populate the legacy
      # Dashboards listing UI. Disable the new apiserver toggle so dashboards
      # round-trip through the classic SQL store and show in the list.
      feature_toggles = {
        kubernetesDashboards = false;
        unifiedStorage = false;
      };

      "auth.anonymous" = {
        enabled = false;
      };

      security = {
        admin_user = "admin";
        admin_password = "$__file{${config.sops.secrets."grafana/admin_password".path}}";
        secret_key = "$__file{${config.sops.secrets."grafana/secret_key".path}}";
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
