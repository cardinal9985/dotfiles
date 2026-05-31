{ pkgs, ... }:

{
  nix-mineral = {
    enable = true;
    preset = "compatibility";
    filesystems.enable = false;

    settings = {
      misc.nix-wheel = true;
      etc.generic-machine-id = false;
      entropy.jitterentropy = false;
      system.multilib = true;
      system.yama = "relaxed";
    };
  };

  boot.kernel.sysctl = {
    "net.ipv4.tcp_syncookies" = 1;
    "net.ipv4.conf.all.rp_filter" = 1;
    "net.ipv4.conf.default.rp_filter" = 1;
    "net.ipv4.conf.all.accept_redirects" = 0;
    "net.ipv4.conf.default.accept_redirects" = 0;
    "net.ipv6.conf.all.accept_redirects" = 0;
    "net.ipv4.conf.all.send_redirects" = 0;
    "net.ipv4.conf.all.accept_source_route" = 0;
    "net.ipv6.conf.all.accept_source_route" = 0;
    "kernel.randomize_va_space" = 2;
    "kernel.kptr_restrict" = 2;
    "kernel.dmesg_restrict" = 1;
    "fs.suid_dumpable" = 0;
  };

  security = {
    polkit.enable = true;
    sudo = {
      enable = true;
      wheelNeedsPassword = true;
      execWheelOnly = true;
    };
    apparmor = {
      enable = true;
      killUnconfinedConfinables = false;
    };
  };

  services.journald.extraConfig = ''
    SystemMaxUse=500M
    RuntimeMaxUse=100M
  '';

  environment.systemPackages = [ pkgs.vulnix ];

  systemd.services.vulnix-scan = {
    description = "Vulnix CVE scan";
    environment = {
      DBUS_SESSION_BUS_ADDRESS = "unix:path=/run/user/1000/bus";
    };
    serviceConfig = {
      Type = "oneshot";
      ExecStart = pkgs.writeShellScript "vulnix-scan" ''
        set -euo pipefail
        output=$(${pkgs.vulnix}/bin/vulnix --system 2>&1 || true)
        if echo "$output" | grep -q "CVE"; then
          count=$(echo "$output" | grep -c "CVE" || true)
          ${pkgs.libnotify}/bin/notify-send \
            --urgency=critical \
            --icon=security-medium \
            "Security Alert" \
            "$count CVE(s) found — run 'journalctl -u vulnix-scan' for details"
        fi
        echo "$output"
      '';
    };
  };

  systemd.timers.vulnix-scan = {
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "weekly";
      Persistent = true;
    };
  };
}
