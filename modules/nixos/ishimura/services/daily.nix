{ inputs, config, ... }:

{
  imports = [ inputs.daily.nixosModules.default ];

  services.daily = {
    enable = true;
    environmentFile = config.sops.templates."daily.env".path;
  };

  systemd.tmpfiles.rules = [
    "d /persist/daily 0750 daily daily -"
  ];

  environment.persistence."/persist".directories = [
    {
      directory = "/persist/daily";
      user = "daily";
      group = "daily";
      mode = "0750";
    }
  ];

  sops.templates."daily.env" = {
    owner = "daily";
    content = ''
      DAILY_DB_PATH=/persist/daily/daily.db
      DAILY_PORT=5011
      DAILY_NASA_API_KEY=${config.sops.placeholder."daily/nasa_api_key"}
      DAILY_USER_LATITUDE=45
    '';
  };
}
