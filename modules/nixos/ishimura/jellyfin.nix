{ ... }:

{
  services.jellyfin.enable = true;

  users.groups.media = {};
  users.users.jellyfin.extraGroups = [ "media" ];

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/jellyfin"; user = "jellyfin"; group = "jellyfin"; mode = "0700"; }
  ];
}
