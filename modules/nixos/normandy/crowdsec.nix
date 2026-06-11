{ ... }:

{
  services.crowdsec = {
    enable = true;

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
