{ config, pkgs, lib, ... }:

{
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
