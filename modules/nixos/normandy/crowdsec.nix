{ pkgs, ... }:

{
  networking.firewall.interfaces.podman1.allowedTCPPorts = [ 8081 ];
  # Expose CrowdSec's Prometheus metrics to the tailnet so ishimura's
  # Prometheus can scrape it.
  networking.firewall.interfaces."tailscale0".allowedTCPPorts = [ 6060 ];

  environment.etc."crowdsec/parsers/s02-enrich/tailnet-whitelist.yaml".source = pkgs.writeText "tailnet-whitelist.yaml" ''
    name: maxwell/tailnet-whitelist
    description: "Whitelist tailnet sources (100.64.0.0/10): operator traffic, not threats"
    whitelist:
      reason: "tailnet operator traffic"
      cidr:
        - "100.64.0.0/10"
  '';

  services.crowdsec = {
    enable = true;

    settings = {
      general.api.server.enable = true;
      general.api.server.listen_uri = "0.0.0.0:8081";
      general.prometheus.enabled = true;
      general.prometheus.level = "full";
      general.prometheus.listen_addr = "0.0.0.0";
      general.prometheus.listen_port = 6060;
      lapi.credentialsFile = "/var/lib/crowdsec/local_api_credentials.yaml";
    };

    localConfig.acquisitions = [
      {
        source = "journalctl";
        journalctl_filter = [ "_SYSTEMD_UNIT=sshd.service" ];
        labels.type = "syslog";
      }
      {
        filenames = [ "/persist/pangolin/config/traefik/logs/access.log" ];
        labels.type = "traefik";
      }
    ];
  };
}
