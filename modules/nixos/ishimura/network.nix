{ ... }:

{
  services.tailscale.extraUpFlags = [ "--accept-dns=false" ];

  networking.networkmanager.dns = "none";

  networking = {
    hostName = "ishimura";
    useDHCP = true;

    nameservers = [ "127.0.0.1" "9.9.9.9" "149.112.112.112" ];

    # Force pangolin.ishimura.lol to resolve to normandy's tailnet IP so newt's
    # WebSocket/API pull hits Traefik via the tailscale0 interface and passes
    # the tailnet-only middleware. Without this, newt sources from ishimura's
    # public-facing IP and gets 403'd at the proxy.
    extraHosts = ''
      100.108.98.70 pangolin.ishimura.lol
    '';

    firewall = {
      enable = true;
      allowedTCPPorts = [
        22    # endlessh honeypot
        36475 # SSH
      ];
    };
  };
}
