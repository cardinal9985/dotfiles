{ config, ... }:

{
  # Pre-declare user+group so sops can resolve owner = "invidious" at eval
  # time. services.invidious also declares this user; NixOS merges the
  # definitions cleanly.
  users.users.invidious = {
    isSystemUser = true;
    group = "invidious";
  };
  users.groups.invidious = {};

  sops.secrets."invidious/hmac_key" = {
    mode = "0400";
  };

  # services.invidious's start script reads the hmacKeyFile as a JSON document
  # and merges it into the runtime config via jq. Raw hex string fails jq's
  # JSON parser; wrap the sops secret in a {"hmac_key": "..."} JSON envelope
  # via a sops template.
  sops.templates."invidious-hmac.json" = {
    content = ''
      {"hmac_key": "${config.sops.placeholder."invidious/hmac_key"}"}
    '';
    owner = "invidious";
  };

  services.invidious = {
    enable = true;
    domain = "invidious.ishimura.lol";
    port = 3939;
    nginx.enable = false;
    hmacKeyFile = config.sops.templates."invidious-hmac.json".path;
  };

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/postgresql"; user = "postgres"; group = "postgres"; mode = "0700"; }
  ];
}
