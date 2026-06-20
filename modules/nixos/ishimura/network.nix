{ ... }:

{
  services.tailscale.extraUpFlags = [ "--accept-dns=false" ];

  networking.networkmanager.dns = "none";

  networking = {
    hostName = "ishimura";
    useDHCP = true;

    nameservers = [ "127.0.0.1" "9.9.9.9" "149.112.112.112" ];
    firewall = {
      enable = true;
      allowedTCPPorts = [
        22    # endlessh honeypot
        36475 # SSH
      ];
    };
  };
}
