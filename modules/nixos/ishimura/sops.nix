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
      "newt/secret" = {
        mode = "0400";
      };
      "crowdsec/ishimura_machine_password" = {
        mode = "0400";
      };
      "crowdsec/ishimura_firewall_bouncer_api_key" = {
        mode = "0400";
      };
      "pelican/app_key" = {
        mode = "0400";
      };
      "invidious/hmac_key" = {
        mode = "0400";
        owner = "invidious";
      };
    };
  };
}
