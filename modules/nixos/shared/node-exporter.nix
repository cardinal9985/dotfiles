{ ... }:

{
  services.prometheus.exporters.node = {
    enable = true;
    enabledCollectors = [
      "systemd"
      "logind"
      "processes"
      "interrupts"
      "filesystem"
      "loadavg"
      "meminfo"
      "diskstats"
      "netstat"
      "stat"
      "uname"
      "cpu"
    ];
    port = 9100;
    listenAddress = "0.0.0.0";
    # We restrict access via firewall below rather than openFirewall=true,
    # which would expose 9100 on every interface (including Normandy's public).
    openFirewall = false;
  };

  # Tailnet-only access. Tailscale interface is already in trustedInterfaces
  # via shared/tailscale.nix, but listing the port explicitly here makes the
  # intent clear and works even if tailscale0 isn't in the trusted list.
  networking.firewall.interfaces."tailscale0".allowedTCPPorts = [ 9100 ];
}
