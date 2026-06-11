{ config, ... }:

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
      nftables = {
        ipv4 = {
          enabled = true;
          table = "crowdsec";
          chain = "crowdsec-chain";
        };
        ipv6 = {
          enabled = true;
          table = "crowdsec6";
          chain = "crowdsec6-chain";
        };
      };
    };
  };
}
