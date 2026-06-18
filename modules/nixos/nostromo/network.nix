{ ... }:

{
  networking = {
    hostName = "nostromo";
    networkmanager = {
      enable = true;
      # AGH (LAN), AGH (tailnet) - tried in order before DHCP-provided DNS.
      insertNameservers = [ "192.168.254.186" "100.92.76.121" ];
    };
    firewall = {
      enable = true;
      allowedTCPPorts = [ 36475 43122 39387 ]; # 36475 = SSH 43122 = Nicotine
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
