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
      allowedTCPPorts = [
        22    # endlessh honeypot
        36475 # real SSH
        80    # Pangolin / Traefik (HTTP, ACME challenges)
        443   # Pangolin / Traefik (HTTPS)
      ];
      allowedUDPPorts = [
        51820 # Pangolin / Gerbil (WireGuard, primary)
        21820 # Pangolin / Gerbil (WireGuard, secondary)
      ];
    };
  };
}
