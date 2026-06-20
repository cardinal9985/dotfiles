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
    openFirewall = false;
  };

  networking.firewall.interfaces."tailscale0".allowedTCPPorts = [ 9100 ];
}
