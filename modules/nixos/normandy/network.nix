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
    nameservers = [ "9.9.9.9" "149.112.112.112" ];
    firewall = {
      enable = true;
      allowedTCPPorts = [
        22    # endlessh honeypot
        36475 # real SSH
        80    # Pangolin / Traefik (HTTP, ACME challenges)
        443   # Pangolin / Traefik (HTTPS)
        50300 # slskd peer port (Pangolin raw resource -> ishimura tailnet:50300)
      ];
      allowedUDPPorts = [
        51820 # Pangolin / Gerbil (WireGuard, primary)
        21820 # Pangolin / Gerbil (WireGuard, secondary)
        42420 # Vintage Story (Pelican raw resource -> nostromo tailnet:42420)
      ];
      interfaces.tailscale0.allowedTCPPorts = [
        3890 # voidauth LDAP (tailnet-only, jellyfin-plugin-ldap connects here)
      ];
    };
  };
}
