{ config, pkgs, lib, ... }:

{
  networking.firewall.interfaces.podman1.allowedTCPPorts = [ 8081 ];

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
      lapi.credentialsFile = "/var/lib/crowdsec/local_api_credentials.yaml";
    };

    localConfig.acquisitions = [
      {
        source = "journalctl";
        journalctl_filter = [ "_SYSTEMD_UNIT=sshd.service" ];
        labels.type = "syslog";
      }
      {
        source = "journalctl";
        journalctl_filter = [ "_SYSTEMD_UNIT=endlessh-go.service" ];
        labels.type = "syslog";
      }
      {
        filenames = [ "/persist/pangolin/config/traefik/logs/access.log" ];
        labels.type = "traefik";
      }
    ];
  };

  services.crowdsec-firewall-bouncer = {
    enable = true;
    registerBouncer.enable = false;
    secrets.apiKeyPath = config.sops.secrets."crowdsec/firewall_bouncer_api_key".path;
    settings = {
      api_url = "http://127.0.0.1:8081/";
      mode = "nftables";
      update_frequency = "10s";
      log_level = "info";
    };
  };

  systemd.services.crowdsec-firewall-bouncer.serviceConfig.ExecStartPre = lib.mkBefore [
    (pkgs.writeShellScript "crowdsec-bouncer-tables" ''
      ${pkgs.nftables}/bin/nft add table ip crowdsec 2>/dev/null || true
      ${pkgs.nftables}/bin/nft 'add chain ip crowdsec crowdsec-chain { type filter hook input priority -10; policy accept; }' 2>/dev/null || true
      ${pkgs.nftables}/bin/nft add table ip6 crowdsec6 2>/dev/null || true
      ${pkgs.nftables}/bin/nft 'add chain ip6 crowdsec6 crowdsec6-chain { type filter hook input priority -10; policy accept; }' 2>/dev/null || true
    '')
  ];
}
