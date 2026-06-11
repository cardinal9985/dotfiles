{ ... }:

{
  sops = {
    age.sshKeyPaths = [ "/etc/ssh/ssh_host_ed25519_key" ];
    defaultSopsFile = ../../../secrets/secrets.yaml;
    defaultSopsFormat = "yaml";

    secrets = {
      "users/maxwell_password" = {
        neededForUsers = true;
      };
      "pangolin/server_secret" = {
        mode = "0400";
      };
    };
  };
}
