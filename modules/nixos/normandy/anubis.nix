{ config, ... }:

{
  sops.secrets."anubis/ed25519_key" = {
    owner = "anubis";
    group = "anubis";
    mode = "0400";
  };

  services.anubis = {
    defaultOptions = {
      # Shared cookie domain so passing the challenge on auth.ishimura.lol
      # also covers ishimura.lol (and any other future subdomain). For this
      # to actually work, both instances must use the SAME ED25519 signing
      # key. Without ED25519_PRIVATE_KEY_HEX_FILE each instance generates
      # a random key at startup, making cross-instance cookies invalid
      # and forcing the user to solve PoW per-subdomain.
      extraFlags = [ "-cookie-domain" ".ishimura.lol" ];

      settings = {
        ED25519_PRIVATE_KEY_HEX_FILE = config.sops.secrets."anubis/ed25519_key".path;
      };

      policy.settings = {
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
        TARGET = "http://127.0.0.1:3030";  # voidauth
        SERVE_ROBOTS_TXT = false;
        OG_PASSTHROUGH = true;
        WEBMASTER_EMAIL = "fanatical.despise915@simplelogin.com";
      };
    };

    instances.homepage = {
      settings = {
        BIND = "127.0.0.1:8925";
        BIND_NETWORK = "tcp";
        METRICS_BIND = "127.0.0.1:8926";
        METRICS_BIND_NETWORK = "tcp";
        TARGET = "http://127.0.0.1:8086";  # static homepage container
        SERVE_ROBOTS_TXT = false;
        OG_PASSTHROUGH = true;
        WEBMASTER_EMAIL = "fanatical.despise915@simplelogin.com";
      };
    };
  };
}
