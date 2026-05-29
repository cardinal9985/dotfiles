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
    dnssec = "allow-downgrade";
    domains = [ "~." ];
    fallbackDns = [ "9.9.9.9" "149.112.112.112" ];
  };

}
