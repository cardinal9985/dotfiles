{ ... }:

{
  networking = {
    hostName = "ishimura";
    useDHCP = true;
    # Point at local AdGuard Home (127.0.0.1:53). dns.nix disables
    # systemd-resolved to free port 53 for AGH. Quad9 listed as fallback so
    # ishimura keeps DNS if AGH or Unbound crashes.
    nameservers = [ "127.0.0.1" "9.9.9.9" "149.112.112.112" ];
    firewall = {
      enable = true;
      allowedTCPPorts = [
        22    # endlessh honeypot
        36475 # real SSH
      ];
    };
  };
}
