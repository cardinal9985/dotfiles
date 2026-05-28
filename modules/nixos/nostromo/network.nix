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

}
