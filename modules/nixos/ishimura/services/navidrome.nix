{ ... }:

let
  tailnetIP = "100.92.76.121";
  normandyTailnet = "100.108.98.70";
in
{
  services.navidrome = {
    enable = true;
    settings = {
      Address = tailnetIP;
      Port = 4533;
      MusicFolder = "/mnt/storage/media/music";
      DataFolder = "/var/lib/navidrome";
      ReverseProxyUserHeader = "Remote-User";
      ReverseProxyWhitelist = "${normandyTailnet}/32";
      EnableTranscodingConfig = true;
      LogLevel = "info";
    };
  };

  users.users.navidrome.extraGroups = [ "gamemode" ];

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/navidrome"; user = "navidrome"; group = "navidrome"; mode = "0700"; }
  ];
}
