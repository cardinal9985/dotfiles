{ ... }:

let
  hosts = import ../../shared/lib/hosts.nix;
in
{
  services.navidrome = {
    enable = true;
    settings = {
      Address = hosts.ishimura.tailnet;
      Port = 4533;
      MusicFolder = "/mnt/storage/media/music";
      DataFolder = "/var/lib/navidrome";
      ReverseProxyUserHeader = "Remote-User";
      ReverseProxyWhitelist = "${hosts.normandy.tailnet}/32";
      EnableTranscodingConfig = true;
      LogLevel = "info";
      Prometheus = {
        Enabled = true;
      };
    };
  };

  users.users.navidrome.extraGroups = [ "gamemode" ];

  environment.persistence."/persist".directories = [
    {
      directory = "/var/lib/navidrome";
      user = "navidrome";
      group = "navidrome";
      mode = "0700";
    }
  ];
}
