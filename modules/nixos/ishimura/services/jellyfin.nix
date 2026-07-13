{ ... }:

{
  services.jellyfin.enable = true;

  users.groups.media = {};
  users.users.jellyfin.extraGroups = [ "media" "video" "render" ];

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/jellyfin"; user = "jellyfin"; group = "jellyfin"; mode = "0700"; }
  ];

  # 8096 HTTP - Jellyfin web/API
  # 7359 UDP - Jellyfin's own server-discovery broadcast
  # 1900 UDP - DLNA discovery (older TVs)
  networking.firewall.allowedTCPPorts = [ 8096 ];
  networking.firewall.allowedUDPPorts = [ 7359 1900 ];
}
