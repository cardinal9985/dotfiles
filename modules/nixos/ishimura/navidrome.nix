{ ... }:

let
  tailnetIP = "100.92.76.121";  # ishimura
  normandyTailnet = "100.108.98.70";  # Normandy's tailnet IP, the only thing
                                       # allowed to set the Remote-User header
in
{
  services.navidrome = {
    enable = true;
    settings = {
      Address = tailnetIP;
      Port = 4533;
      MusicFolder = "/mnt/storage/media/music";
      DataFolder = "/var/lib/navidrome";
      # voidauth-forwardauth on Normandy sets Remote-User; Navidrome trusts it
      # only when the inbound request is from Normandy's tailnet IP. Subsonic
      # API clients (/rest/*) bypass voidauth at the Pangolin layer and use
      # native Subsonic auth - users set their own Subsonic password in the
      # Navidrome UI after first sign-in.
      ReverseProxyUserHeader = "Remote-User";
      ReverseProxyWhitelist = "${normandyTailnet}/32";
      EnableTranscodingConfig = true;
      LogLevel = "info";
    };
  };

  # /mnt/storage/media is owned by maxwell:gamemode (mode 0775). Add navidrome
  # to gamemode so it can read the music library without making it world-rw.
  users.users.navidrome.extraGroups = [ "gamemode" ];

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/navidrome"; user = "navidrome"; group = "navidrome"; mode = "0700"; }
  ];
}
