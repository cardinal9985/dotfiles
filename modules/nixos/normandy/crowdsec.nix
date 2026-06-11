{ ... }:

{
  services.crowdsec = {
    enable = true;

    settings = {
      general.api.server.enable = true;
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
