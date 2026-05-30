{ ... }:

{
  networking = {
    hostName = "nostromo";
    networkmanager.enable = true;
    firewall = {
      enable = true;
      allowedTCPPorts = [ 36475 ]; # 36475 = SSH
    };
  };

  services.resolved = {
    enable = true;
    settings.Resolve = {
      DNSSEC = "allow-downgrade";
      Domains = [ "~." ];
      FallbackDNS = [ "9.9.9.9" "149.112.112.112" ];
    };
  };
}
