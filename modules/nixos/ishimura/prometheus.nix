{ ... }:

{
  services.prometheus = {
    enable = true;
    port = 9090;
    # Bind 0.0.0.0; firewall below restricts ingress to the tailnet interface.
    listenAddress = "0.0.0.0";
    retentionTime = "30d";

    globalConfig = {
      scrape_interval = "30s";
      evaluation_interval = "30s";
    };

    # Targets use MagicDNS short names so tailnet IP drift (per the NFS
    # incident from 2026-06-13) does not break scraping.
    scrapeConfigs = [
      {
        job_name = "node";
        static_configs = [{
          targets = [
            "127.0.0.1:9100"   # ishimura (local)
            "nostromo:9100"
            "normandy:9100"
          ];
          labels = {
            role = "host";
          };
        }];
      }
      {
        job_name = "crowdsec";
        static_configs = [{
          targets = [ "normandy:6060" ];
          labels = {
            role = "security";
          };
        }];
      }
    ];
  };

  networking.firewall.interfaces."tailscale0".allowedTCPPorts = [ 9090 ];
}
