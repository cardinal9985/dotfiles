{ ... }:

{
  services.anubis.instances.public = {
    settings = {
      BIND = "127.0.0.1:8923";
      BIND_NETWORK = "tcp";
      METRICS_BIND = "127.0.0.1:8924";
      METRICS_BIND_NETWORK = "tcp";
      TARGET = "http://127.0.0.1:3030";
      DIFFICULTY = 4;
      SERVE_ROBOTS_TXT = true;
      OG_PASSTHROUGH = true;
      WEBMASTER_EMAIL = "fanatical.despise915@simplelogin.com";
    };
  };
}
