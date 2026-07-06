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
      "booklore/db_password" = {
        mode = "0400";
      };
      "romm/db_password" = {
        mode = "0400";
      };
      "romm/auth_secret_key" = {
        mode = "0400";
      };
      "romm/igdb_client_id" = {
        mode = "0400";
      };
      "romm/igdb_client_secret" = {
        mode = "0400";
      };
      "romm/steamgriddb_api_key" = {
        mode = "0400";
      };
      "romm/retroachievements_api_key" = {
        mode = "0400";
      };
      "romm/screenscraper_user" = {
        mode = "0400";
      };
      "romm/screenscraper_password" = {
        mode = "0400";
      };
      "romm/oidc_client_id" = {
        mode = "0400";
      };
      "romm/oidc_client_secret" = {
        mode = "0400";
      };
      "requests/tmdb_token" = {
        mode = "0400";
      };
      "stats/jellyfin_api_key" = {
        mode = "0400";
      };
      "stats/webhook_secret" = {
        mode = "0400";
      };
      "stats/lastfm_api_key" = {
        mode = "0400";
      };
      "stats/twitch_client_id" = {
        mode = "0400";
      };
      "stats/twitch_client_secret" = {
        mode = "0400";
      };
      "slskd/slsk_username" = {
        mode = "0400";
      };
      "slskd/slsk_password" = {
        mode = "0400";
      };
      "searxng/secret_key" = {
        mode = "0400";
      };
      "chess/secret_key" = {
        mode = "0400";
      };
      "chess/discord_webhook" = {
        mode = "0400";
      };
    };
  };
}
