{ ... }:

{
  networking = {
    hostName = "ishimura";
    useDHCP = true;
    firewall = {
      enable = true;
      allowedTCPPorts = [
        22    # endlessh honeypot
        36475 # real SSH
      ];
    };
  };

  services.resolved = {
    enable = true;
    settings.Resolve = {
      DNSSEC = "false";
      FallbackDNS = [ "9.9.9.9" "149.112.112.112" ];
    };
  };
}
