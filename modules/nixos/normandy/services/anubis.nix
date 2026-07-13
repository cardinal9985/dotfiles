{ config, ... }:

{
  sops.secrets."anubis/ed25519_key" = {
    owner = "anubis";
    group = "anubis";
    mode = "0400";
  };

  sops.secrets."anubis/webmaster_email" = {};

  sops.templates."anubis-public.env" = {
    content = ''
      WEBMASTER_EMAIL=${config.sops.placeholder."anubis/webmaster_email"}
    '';
    owner = "anubis";
  };

  systemd.services.anubis-public.serviceConfig.EnvironmentFile =
    config.sops.templates."anubis-public.env".path;

  services.anubis = {
    defaultOptions = {
      extraFlags = [ "-cookie-domain" ".ishimura.lol" ];

      settings = {
        ED25519_PRIVATE_KEY_HEX_FILE = config.sops.secrets."anubis/ed25519_key".path;
      };

      policy.settings = {
        bots = [
          {
            name = "oidc-endpoints";
            path_regex = "^/oidc/.*";
            action = "ALLOW";
          }
          {
            name = "well-known";
            path_regex = "^/\\.well-known/.*";
            action = "ALLOW";
          }
        ];
        thresholds = [
          {
            name = "minimal-suspicion";
            expression = "weight <= 0";
            action = "ALLOW";
          }
          {
            name = "mild-suspicion";
            expression = "weight > 0 && weight < 20";
            action = "CHALLENGE";
            challenge = {
              algorithm = "fast";
              difficulty = 4;
            };
          }
          {
            name = "moderate-suspicion";
            expression = "weight >= 20 && weight < 30";
            action = "CHALLENGE";
            challenge = {
              algorithm = "fast";
              difficulty = 5;
            };
          }
          {
            name = "extreme-suspicion";
            expression = "weight >= 30";
            action = "CHALLENGE";
            challenge = {
              algorithm = "fast";
              difficulty = 6;
            };
          }
        ];
      };
    };

    instances.public = {
      settings = {
        BIND = "127.0.0.1:8923";
        BIND_NETWORK = "tcp";
        METRICS_BIND = "127.0.0.1:8924";
        METRICS_BIND_NETWORK = "tcp";
        TARGET = "http://127.0.0.1:3030";
        SERVE_ROBOTS_TXT = false;
        OG_PASSTHROUGH = true;
      };
    };
  };
}
