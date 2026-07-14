{ inputs, config, ... }:

{
  imports = [ inputs.bridge.nixosModules.default ];

  services.bridge = {
    enable = true;
    environmentFile = config.sops.templates."bridge.env".path;
  };

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
    '';
  };
}
