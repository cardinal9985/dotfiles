{ ... }:

{
  networking = {
    hostName = "nostromo";
    networkmanager = {
      enable = true;
      insertNameservers = [ "192.168.254.186" "100.92.76.121" ];
      # Stop NM from auto-creating a DHCP "Wired connection 1" profile that
      # races our static profile to the device and pins the wrong IP. With
      # no-auto-default=*, only ensureProfiles entries get applied.
      settings.main.no-auto-default = "*";
      # Static IP profile so NM manages enp8s0 and reports connected (global),
      # which is required for apps that check NM D-Bus state (e.g. Spotify AP).
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
      "100.108.98.70" = [ "ishimura.lol" "pangolin.ishimura.lol" "auth.ishimura.lol" "files.ishimura.lol" ];
      # Local override: games.ishimura.lol bypasses router NAT loopback when
      # we're on the LAN. Friend's DNS still gets the public IP from Porkbun.
      "192.168.254.97" = [ "games.ishimura.lol" ];
    };
  };

  services.resolved = {
    enable = true;
    settings.Resolve = {
      DNSSEC = "false";
      Domains = [ "~." ];
      FallbackDNS = [ "9.9.9.9" "149.112.112.112" ];
    };
  };
}
