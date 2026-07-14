{ inputs, config, ... }:

{
  imports = [ inputs.bridge.nixosModules.default ];

  services.bridge = {
    enable = true;
    environmentFile = config.sops.templates."bridge.env".path;
  };

  # normandy runs bridge itself, so its collector hits loopback rather than looping through traefik
  services.bridge-collector.target = "http://127.0.0.1:5015/api/host-stats/ingest";

  # bridge user needs sudo to control normandy-local podman units
  security.sudo.extraRules = [
    {
      users = [ "bridge" ];
      commands = [
        {
          command = "/run/current-system/sw/bin/systemctl start *";
          options = [ "NOPASSWD" ];
        }
        {
          command = "/run/current-system/sw/bin/systemctl stop *";
          options = [ "NOPASSWD" ];
        }
        {
          command = "/run/current-system/sw/bin/systemctl restart *";
          options = [ "NOPASSWD" ];
        }
        {
          command = "/run/current-system/sw/bin/systemctl is-active *";
          options = [ "NOPASSWD" ];
        }
        {
          command = "/run/current-system/sw/bin/journalctl *";
          options = [ "NOPASSWD" ];
        }
      ];
    }
  ];

  systemd.tmpfiles.rules = [
    "d /persist/bridge 0750 bridge bridge -"
  ];

  environment.persistence."/persist".directories = [
    {
      directory = "/persist/bridge";
      user = "bridge";
      group = "bridge";
      mode = "0750";
    }
  ];

  sops.secrets."bridge/ssh_key" = {
    owner = "bridge";
    mode = "0400";
  };

  sops.templates."bridge.env" = {
    owner = "bridge";
    content = ''
      BRIDGE_DB_PATH=/persist/bridge/bridge.db
      BRIDGE_SSH_KEY=${config.sops.secrets."bridge/ssh_key".path}
      BRIDGE_ISHIMURA_IP=100.92.76.121
      BRIDGE_NOSTROMO_IP=100.107.103.76
      BRIDGE_PORT=5015
      BRIDGE_NTFY_URL=http://127.0.0.1:8080
      BRIDGE_NTFY_TOPIC=ishimura-bridge
      BRIDGE_PORKBUN_API_KEY=${config.sops.placeholder."porkbun/api_key"}
      BRIDGE_PORKBUN_SECRET_KEY=${config.sops.placeholder."porkbun/secret_api_key"}
      BRIDGE_COLLECTOR_TOKEN=${config.sops.placeholder."bridge/collector_token"}
    '';
  };
}
