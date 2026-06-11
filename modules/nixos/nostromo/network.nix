{ ... }:

{
  networking = {
    hostName = "nostromo";
    networkmanager.enable = true;
    firewall = {
      enable = true;
      allowedTCPPorts = [ 36475 43122 39387 ]; # 36475 = SSH 43122 = Nicotine
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
