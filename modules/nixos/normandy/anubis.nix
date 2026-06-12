{ ... }:

{
  services.anubis.instances.public = {
    settings = {
      BIND = "127.0.0.1:8923";
      BIND_NETWORK = "tcp";
      METRICS_BIND = "127.0.0.1:8924";
      METRICS_BIND_NETWORK = "tcp";
      TARGET = "http://127.0.0.1:3030";
      SERVE_ROBOTS_TXT = false;
      OG_PASSTHROUGH = true;
      WEBMASTER_EMAIL = "fanatical.despise915@simplelogin.com";
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
            difficulty = 7;
          };
        }
        {
          name = "moderate-suspicion";
          expression = "weight >= 20 && weight < 30";
          action = "CHALLENGE";
          challenge = {
            algorithm = "fast";
            difficulty = 8;
          };
        }
        {
          name = "extreme-suspicion";
          expression = "weight >= 30";
          action = "CHALLENGE";
          challenge = {
            algorithm = "fast";
            difficulty = 10;
          };
        }
      ];
    };
  };
}
