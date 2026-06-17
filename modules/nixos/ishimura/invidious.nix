{ config, ... }:

{
  sops.secrets."invidious/hmac_key" = {
    mode = "0400";
    owner = "invidious";
  };

  services.invidious = {
    enable = true;
    domain = "invidious.ishimura.lol";
    port = 3939;
    nginx.enable = false;
    hmacKeyFile = config.sops.secrets."invidious/hmac_key".path;
    settings = {
      db = {
        user = "invidious";
        dbname = "invidious";
      };
      check_tables = true;
      external_port = 443;
      https_only = true;
      use_pubsub_feeds = false;
      popular_enabled = false;
      statistics_enabled = false;
      registration_enabled = false;
      login_enabled = false;
      captcha_enabled = false;
      default_user_preferences = {
        dark_mode = "dark";
        quality = "dash";
        quality_dash = "720p";
        save_player_pos = true;
        autoplay = false;
        related_videos = true;
      };
    };
  };

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/postgresql"; user = "postgres"; group = "postgres"; mode = "0700"; }
  ];
}
