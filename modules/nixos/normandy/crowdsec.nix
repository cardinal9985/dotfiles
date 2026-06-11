{ config, pkgs, lib, ... }:

let
  hubCollections = [
    "crowdsecurity/sshd"
    "crowdsecurity/linux"
    "crowdsecurity/base-http-scenarios"
    "crowdsecurity/http-cve"
    "crowdsecurity/traefik"
  ];
in
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

  systemd.services.crowdsec-install-collections = {
    description = "Install CrowdSec hub collections";
    wantedBy = [ "multi-user.target" ];
    after = [ "crowdsec.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.crowdsec}/bin/cscli hub update
      ${lib.concatMapStringsSep "\n" (c: ''
        ${pkgs.crowdsec}/bin/cscli collections install ${c} || true
      '') hubCollections}
    '';
  };
}
