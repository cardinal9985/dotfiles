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

  services.crowdsec-firewall-bouncer = {
    enable = true;
    registerBouncer.enable = false;
    secrets.apiKeyPath = config.sops.secrets."crowdsec/ishimura_firewall_bouncer_api_key".path;
    settings = {
      api_url = "http://100.108.98.70:8081/";
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
