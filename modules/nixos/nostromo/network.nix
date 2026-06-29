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
      "100.108.98.70" = [ "ishimura.lol" "pangolin.ishimura.lol" "auth.ishimura.lol" ];
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
