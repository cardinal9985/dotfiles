{ ... }:

{
  services.jellyfin.enable = true;

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/jellyfin"; user = "jellyfin"; group = "jellyfin"; mode = "0700"; }
  ];
}
