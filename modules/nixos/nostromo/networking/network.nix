{ ... }:

let
  hosts = import ../../shared/lib/hosts.nix;
in
{
  networking = {
    hostName = "nostromo";
    networkmanager = {
      enable = true;
      insertNameservers = [ "192.168.254.186" hosts.ishimura.tailnet ];
      settings.main.no-auto-default = "*";
      ensureProfiles.profiles."enp8s0-static" = {
        connection = {
          id = "enp8s0-static";
          type = "ethernet";
          "interface-name" = "enp8s0";
          autoconnect = "true";
        };
        ipv4 = {
          method = "manual";
          addresses = "192.168.254.97/24";
          gateway = "192.168.254.254";
        };
        ipv6.method = "disabled";
      };
    };
    firewall = {
      enable = true;
      allowedTCPPorts = [
        36475 # SSH
        6969  # SPT.Server HTTP + WebSocket (Fika co-op relay)
        25565 # Fika P2P (raid signaling)
        34123
        8380  # KF2 WebAdmin (tailnet-only, not router-forwarded)
        5010  # Hangar control panel (tailnet-only, fronted by pangolin)
      ];
      allowedUDPPorts = [
        25565 # Fika P2P (raid game traffic)
        6790  # Fika NAT-punch server (Pangolin raw resource > nostromo:6790)
        42420 # Vintage Story
        7777  # KF2 game
        27015 # KF2 Steam query
      ];
    };
    hosts = {
      "${hosts.normandy.tailnet}" = [ "ishimura.lol" "pangolin.ishimura.lol" "auth.ishimura.lol" "files.ishimura.lol" ];
      "192.168.254.97" = [ "games.ishimura.lol" ];
    };
  };

}
