{ ... }:

{
  boot.kernel.sysctl = {
    "vm.max_map_count"               = 2147483642;
    "kernel.sched_autogroup_enabled" = 0;
    "vm.swappiness"                  = 10;
    "vm.dirty_ratio"                 = 10;
    "vm.dirty_background_ratio"      = 5;
    "fs.inotify.max_user_watches"    = 1048576;
    "fs.inotify.max_user_instances"  = 8192;
    "fs.inotify.max_queued_events"   = 32768;
    "net.core.rmem_max"              = 134217728;
    "net.core.wmem_max"              = 134217728;
  };

  security.pam.loginLimits = [
    { domain = "@users"; item = "rtprio";  type = "-";    value = "95";        }
    { domain = "@users"; item = "memlock"; type = "-";    value = "unlimited"; }
    { domain = "@users"; item = "nofile";  type = "soft"; value = "524288";    }
    { domain = "@users"; item = "nofile";  type = "hard"; value = "524288";    }
  ];
}
