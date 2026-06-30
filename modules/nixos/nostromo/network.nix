{ ... }:

{
  networking = {
    hostName = "nostromo";
    networkmanager = {
      enable = true;
      insertNameservers = [ "192.168.254.186" "100.92.76.121" ];
    };
    firewall = {
      enable = true;
      allowedTCPPorts = [
        36475 # SSH
        6969  # SPT.Server (Pelican container, exposed for direct game.ishimura.lol forward)
      ];
      allowedUDPPorts = [
        6790  # Fika game traffic
        42420 # Vintage Story
      ];
    };
    hosts = {
      "100.108.98.70" = [ "ishimura.lol" "pangolin.ishimura.lol" "auth.ishimura.lol" "files.ishimura.lol" ];
      # Local override: games.ishimura.lol bypasses router NAT loopback when
      # we're on the LAN. Friend's DNS still gets the public IP from Porkbun.
      "192.168.254.95" = [ "games.ishimura.lol" ];
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
