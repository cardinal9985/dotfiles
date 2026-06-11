{ ... }:

{
  networking = {
    hostName = "normandy";
    useDHCP = false;
    interfaces.ens18 = {
      useDHCP = false;
      ipv4.addresses = [{
        address = "168.222.97.137";
        prefixLength = 24;
      }];
    };
    defaultGateway = "168.222.97.1";
    nameservers = [ "1.1.1.1" "9.9.9.9" ];
    firewall = {
      enable = true;
      allowedTCPPorts = [ 22 ];
    };
  };
}
