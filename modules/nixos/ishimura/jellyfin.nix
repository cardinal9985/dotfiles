{ ... }:

{
  services.jellyfin.enable = true;

  users.groups.media = {};
  users.users.jellyfin.extraGroups = [ "media" "video" "render" ];

  environment.persistence."/persist".directories = [
    { directory = "/var/lib/jellyfin"; user = "jellyfin"; group = "jellyfin"; mode = "0700"; }
  ];

  # LAN access for family TVs / native clients. tailnet0 is already trusted in
  # shared/tailscale.nix, so this only opens the home LAN interface.
  #   8096  HTTP        : Jellyfin web/API
  #   8920  HTTPS       : unused (we terminate TLS at Traefik) but harmless
  #   7359  UDP         : Jellyfin's own server-discovery broadcast
  #   1900  UDP (SSDP)  : DLNA discovery (older TVs)
  networking.firewall.allowedTCPPorts = [ 8096 8920 ];
  networking.firewall.allowedUDPPorts = [ 7359 1900 ];
}
