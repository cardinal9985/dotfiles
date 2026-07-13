{ inputs, config, ... }:

{
  imports = [ inputs.requests.nixosModules.default ];

  services.requests = {
    enable = true;
    environmentFile = config.sops.templates."requests.env".path;
  };

  systemd.tmpfiles.rules = [
    "d /persist/requests 0750 requests requests -"
  ];

  environment.persistence."/persist".directories = [
    {
      directory = "/persist/requests";
      user = "requests";
      group = "requests";
      mode = "0750";
    }
  ];

  sops.templates."requests.env" = {
    owner = "requests";
    content = ''
      DB_PATH=/persist/requests/requests.db
      TMDB_TOKEN=${config.sops.placeholder."requests/tmdb_token"}
      IGDB_CLIENT_ID=${config.sops.placeholder."romm/igdb_client_id"}
      IGDB_CLIENT_SECRET=${config.sops.placeholder."romm/igdb_client_secret"}
      NTFY_URL=http://normandy:8080
      NTFY_TOPIC=ishimura-requests
      NTFY_TOKEN=
    '';
  };
}
