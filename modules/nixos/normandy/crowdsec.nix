{ ... }:

{
  networking.firewall.interfaces.podman1.allowedTCPPorts = [ 8081 ];

  services.crowdsec = {
    enable = true;

    settings = {
      general.api.server.enable = true;
      general.api.server.listen_uri = "0.0.0.0:8081";
      general.plugin_config.user = "crowdsec";
      general.plugin_config.group = "crowdsec";
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

    localConfig.profiles = [
      {
        name = "default_ip_remediation";
        filters = [ ''Alert.Remediation == true && Alert.GetScope() == "Ip"'' ];
        decisions = [{ type = "ban"; duration = "4h"; }];
        notifications = [ "ntfy-default" ];
        on_success = "break";
      }
    ];
  };

  environment.etc."crowdsec/notifications/ntfy.yaml".text = ''
    type: http
    name: ntfy-default
    log_level: info
    format: |
      {{range . -}}
      🚫 Banned {{.Source.Value}}{{if .Source.Cn}} ({{.Source.Cn}}){{end}} - {{.Scenario}}
      {{end -}}
    url: http://localhost:8080/crowdsec
    method: POST
    headers:
      X-Title: CrowdSec Ban
      X-Tags: shield,no_entry
      X-Priority: default
  '';
}
