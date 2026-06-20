{ ... }:

{
  services.prometheus = {
    enable = true;
    port = 9090;
    listenAddress = "0.0.0.0";
    retentionTime = "30d";

    globalConfig = {
      scrape_interval = "30s";
      evaluation_interval = "30s";
    };

    scrapeConfigs = [
      {
        job_name = "node";
        static_configs = [{
          targets = [
            "127.0.0.1:9100"
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

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/prometheus2"; user = "prometheus"; group = "prometheus"; mode = "0755"; }
  ];
}
