{ config, pkgs, lib, ... }:

let
  hosts = import ../../shared/lib/hosts.nix;
in
{
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
      url: http://${hosts.normandy.tailnet}:8081
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
      api_url = "http://${hosts.normandy.tailnet}:8081/";
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
