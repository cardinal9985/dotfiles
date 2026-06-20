{ pkgs, ... }:

{
  services.loki = {
    enable = true;
    configuration = {
      auth_enabled = false;

      server = {
        http_listen_address = "0.0.0.0";
        http_listen_port = 3100;
        grpc_listen_address = "127.0.0.1";
        grpc_listen_port = 9095;
      };

      common = {
        path_prefix = "/var/lib/loki";
        storage = {
          filesystem = {
            chunks_directory = "/var/lib/loki/chunks";
            rules_directory = "/var/lib/loki/rules";
          };
        };
        replication_factor = 1;
        ring = {
          instance_addr = "127.0.0.1";
          kvstore.store = "inmemory";
        };
      };

      schema_config = {
        configs = [{
          from = "2024-01-01";
          store = "tsdb";
          object_store = "filesystem";
          schema = "v13";
          index = {
            prefix = "index_";
            period = "24h";
          };
        }];
      };

      limits_config = {
        retention_period = "720h";
        reject_old_samples = true;
        reject_old_samples_max_age = "168h";
        max_query_series = 100000;
        ingestion_rate_mb = 16;
        ingestion_burst_size_mb = 32;
      };

      compactor = {
        working_directory = "/var/lib/loki/compactor";
        retention_enabled = true;
        retention_delete_delay = "2h";
        retention_delete_worker_count = 150;
        delete_request_store = "filesystem";
      };

      analytics.reporting_enabled = false;
    };
  };

  systemd.tmpfiles.rules = [
    "d /var/lib/loki         0750 loki loki -"
    "d /var/lib/loki/chunks  0750 loki loki -"
    "d /var/lib/loki/rules   0750 loki loki -"
  ];

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/loki"; user = "loki"; group = "loki"; mode = "0750"; }
  ];

  networking.firewall.interfaces."tailscale0".allowedTCPPorts = [ 3100 ];
}
