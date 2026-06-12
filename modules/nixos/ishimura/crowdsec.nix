{ config, ... }:

{
  services.crowdsec = {
    enable = true;

    settings = {
      general.api.server.enable = false;
      lapi.credentialsFile = config.sops.templates."crowdsec-credentials.yaml".path;
    };

    localConfig.acquisitions = [
      {
        source = "journalctl";
        journalctl_filter = [ "_SYSTEMD_UNIT=sshd.service" ];
        labels.type = "syslog";
      }
    ];
  };

  sops.templates."crowdsec-credentials.yaml" = {
    content = ''
      url: http://100.108.98.70:8081
      login: ishimura
      password: ${config.sops.placeholder."crowdsec/ishimura_machine_password"}
    '';
    owner = "crowdsec";
    group = "crowdsec";
    mode = "0400";
  };
}
