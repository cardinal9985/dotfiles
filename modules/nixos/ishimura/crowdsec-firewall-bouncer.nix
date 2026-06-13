{ config, pkgs, lib, ... }:

{
  services.crowdsec-firewall-bouncer = {
    enable = true;
    registerBouncer.enable = false;
    secrets.apiKeyPath = config.sops.secrets."crowdsec/ishimura_firewall_bouncer_api_key".path;
    settings = {
      # Federated LAPI lives on Normandy. ishimura's local bouncer polls the
      # remote LAPI every 10s and applies the unified ban list to nftables.
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
