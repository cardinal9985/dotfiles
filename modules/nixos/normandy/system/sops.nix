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
      "crowdsec/firewall_bouncer_api_key" = {
        mode = "0400";
      };
      "crowdsec/traefik_bouncer_api_key" = {
        mode = "0400";
      };
      "voidauth/storage_key" = {
        mode = "0400";
      };
      "voidauth/db_password" = {
        mode = "0400";
      };
      "voidauth/ldap_bind_password" = {
        mode = "0400";
      };
      "voidauth/smtp_password" = {
        mode = "0400";
      };
      "coturn/static_auth_secret" = {
        owner = "turnserver";
        group = "turnserver";
        mode = "0400";
      };
      "porkbun/api_key" = {
        mode = "0400";
      };
      "porkbun/secret_api_key" = {
        mode = "0400";
      };
      "searxng/secret_key" = {
        mode = "0400";
      };
    };
  };
}
