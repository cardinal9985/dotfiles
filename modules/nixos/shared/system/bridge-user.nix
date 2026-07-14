{ ... }:

{
  # SSH target user for Bridge dispatch from normandy.
  # After generating the key pair:
  #   ssh-keygen -t ed25519 -f bridge_key -C "bridge@normandy" -N ""
  # Replace the placeholder below with the contents of bridge_key.pub,
  # then add bridge_key (private) to secrets/secrets.yaml as bridge/ssh_key.
  users.users.bridge = {
    isSystemUser = true;
    group = "bridge";
    useDefaultShell = true;
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAYojLHN87/Ae/Ba+7truhAMnsKqo0SfNvO7jBGnGna6 bridge@normandy"
    ];
  };
  users.groups.bridge = { };

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
        {
          command = "/run/current-system/sw/bin/cat /persist/pangolin/config/letsencrypt/acme.json";
          options = [ "NOPASSWD" ];
        }
      ];
    }
  ];
}
